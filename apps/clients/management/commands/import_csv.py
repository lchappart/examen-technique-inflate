from django.core.management.base import BaseCommand
from django.db import transaction  # <--- 1. L'import indispensable
from apps.clients.models import Client, UserClient
from apps.orders.models import Order
import csv
import json
from tqdm import tqdm

class Command(BaseCommand):
    help = 'Importe les clients et commandes depuis un CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file', 
            nargs='?',             
            default='sample_data.csv', 
            type=str,
            help='Le chemin vers le fichier CSV à importer'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',   
            help='Simule l\'import sans sauvegarder les changements en base'
        )

    def handle(self, *args, **options): #Gère l'importation des données en CSV avec différents arguments
        file_path = options['csv_file']
        dry_run = options['dry_run']
        verbosity = options['verbosity']

        self.stdout.write(self.style.SUCCESS(f"Lecture du fichier : {file_path}"))
        
        if dry_run:
            self.stdout.write(self.style.WARNING("Mode Dry-Run activé. Aucune modification ne sera sauvegardée. 🛡️"))

        try:
            with transaction.atomic():
                with open(file_path, 'r', encoding='utf-8') as file:
                    reader = csv.DictReader(file) 
                    
                    for row in tqdm(reader):
                        client, created = Client.objects.get_or_create(
                            email=row['client_email'],
                            defaults={
                                "shop": row['client_shop'], 
                                "first_name": row['client_first_name'], 
                                "last_name": row['client_last_name']
                            }
                        )
                        
                        user_client, created = UserClient.objects.get_or_create(
                            email=row['user_email'],
                            from_client=client,
                            defaults={
                                "name": row['user_name'],
                                "last_name": row['user_last_name'],
                                "location": row['user_location'],
                                "from_client": client
                            }
                        )
                        
                        order, created = Order.objects.get_or_create(
                            order_id=row['order_id'],
                            from_client=client,
                            defaults={
                                "product_id": json.loads(row['product_ids']),
                                "customer_email": row['user_email'],
                                "customer_name": row['user_name'],
                                "mail_sent": False,
                                "mail_sent_at": None
                            }
                        )
                        
                        if verbosity >= 2:
                            self.stdout.write(f"Traitement : {order.order_id} pour {client.email}")

                if dry_run:
                    raise Exception("DryRunRollback")
                else:
                    self.stdout.write(self.style.SUCCESS("Import terminé avec succès ! 🚀"))

        except Exception as e:
            if str(e) == "DryRunRollback":
                self.stdout.write(self.style.SUCCESS("Simulation terminée. La base de données est restée intacte. 🧹"))
            else:
                self.stdout.write(self.style.ERROR(f"Une erreur est survenue : {e}"))
                raise e