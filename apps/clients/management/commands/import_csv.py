from django.core.management.base import BaseCommand
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from apps.clients.models import Client, UserClient
from apps.orders.models import Order
from tqdm import tqdm
import csv
import json
import os
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Importe les clients et commandes depuis un CSV'

    # Colonnes requises dans le CSV
    REQUIRED_COLUMNS = [
        'client_email',
        'client_shop',
        'client_first_name',
        'client_last_name',
        'user_email',
        'user_name',
        'user_last_name',
        'user_location',
        'order_id',
        'product_ids'
    ]

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

    def validate_email_address(self, email, field_name, line_number):
        """Valide une adresse email et retourne l'email ou None si invalide"""
        if not email or not email.strip():
            return None, f"Ligne {line_number}: {field_name} est vide"
        
        email = email.strip()
        try:
            validate_email(email)
            return email, None
        except ValidationError:
            return None, f"Ligne {line_number}: {field_name} '{email}' n'est pas une adresse email valide"

    def validate_columns(self, reader):
        """Valide que toutes les colonnes requises sont présentes dans le CSV"""
        if not reader.fieldnames:
            raise ValueError("Le fichier CSV est vide ou ne contient pas d'en-têtes")
        
        missing_columns = set(self.REQUIRED_COLUMNS) - set(reader.fieldnames)
        if missing_columns:
            raise ValueError(
                f"Colonnes manquantes dans le CSV : {', '.join(sorted(missing_columns))}. "
                f"Colonnes requises : {', '.join(self.REQUIRED_COLUMNS)}"
            )
        
        return True

    def validate_json_field(self, json_string, field_name, line_number):
        """Valide et parse un champ JSON"""
        if not json_string or not json_string.strip():
            return None, f"Ligne {line_number}: {field_name} est vide"
        
        try:
            parsed = json.loads(json_string.strip())
            if not isinstance(parsed, list):
                return None, f"Ligne {line_number}: {field_name} doit être une liste JSON"
            return parsed, None
        except json.JSONDecodeError as e:
            return None, f"Ligne {line_number}: {field_name} contient du JSON invalide : {str(e)}"

    def handle(self, *args, **options): #Gère l'importation des données en CSV avec différents arguments
        file_path = options['csv_file']
        dry_run = options['dry_run']
        verbosity = options['verbosity']

        logger.info(f"Démarrage de l'import CSV : {file_path}")
        self.stdout.write(self.style.SUCCESS(f"Lecture du fichier : {file_path}"))
        
        if dry_run:
            logger.warning("Mode Dry-Run activé. Aucune modification ne sera sauvegardée.")
            self.stdout.write(self.style.WARNING("Mode Dry-Run activé. Aucune modification ne sera sauvegardée. 🛡️"))

        # Vérifier que le fichier existe
        if not os.path.exists(file_path):
            error_msg = f"Le fichier '{file_path}' est introuvable."
            logger.error(error_msg)
            self.stdout.write(self.style.ERROR(f"Erreur : {error_msg}"))
            return

        errors = []
        success_count = 0
        skipped_count = 0

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                # Valider les colonnes avant de traiter les données
                try:
                    self.validate_columns(reader)
                    logger.info("Validation des colonnes réussie")
                except ValueError as e:
                    error_msg = f"Erreur de validation des colonnes : {e}"
                    logger.error(error_msg)
                    self.stdout.write(self.style.ERROR(error_msg))
                    return
                
                # Compter les lignes de données (sans l'en-tête)
                total_lines = sum(1 for _ in file) - 1
                file.seek(0)
                reader = csv.DictReader(file)  # Réinitialiser le reader
                
                if total_lines > 0:
                    logger.info(f"Colonnes validées. Début du traitement de {total_lines} ligne(s) de données")
                    self.stdout.write(self.style.SUCCESS(f"Colonnes validées. Début du traitement de {total_lines} ligne(s) de données..."))
                else:
                    warning_msg = "Le fichier CSV ne contient aucune ligne de données (seulement les en-têtes)."
                    logger.warning(warning_msg)
                    self.stdout.write(self.style.WARNING(warning_msg))
                    return

                with transaction.atomic():
                    for line_number, row in enumerate(tqdm(reader, total=total_lines, desc="Import"), start=2):  # start=2 car ligne 1 = en-têtes
                        row_errors = []
                        
                        # Validation des emails
                        client_email, email_error = self.validate_email_address(
                            row.get('client_email'), 'client_email', line_number
                        )
                        if email_error:
                            row_errors.append(email_error)
                        
                        user_email, email_error = self.validate_email_address(
                            row.get('user_email'), 'user_email', line_number
                        )
                        if email_error:
                            row_errors.append(email_error)
                        
                        # Validation du champ product_ids (JSON)
                        product_ids, json_error = self.validate_json_field(
                            row.get('product_ids'), 'product_ids', line_number
                        )
                        if json_error:
                            row_errors.append(json_error)
                        
                        # Validation des champs obligatoires non-email
                        required_fields = {
                            'client_shop': row.get('client_shop'),
                            'order_id': row.get('order_id'),
                        }
                        
                        for field_name, field_value in required_fields.items():
                            if not field_value or not field_value.strip():
                                row_errors.append(f"Ligne {line_number}: {field_name} est vide")
                        
                        # Si des erreurs de validation, on skip cette ligne
                        if row_errors:
                            errors.extend(row_errors)
                            skipped_count += 1
                            error_details = '; '.join(row_errors)
                            logger.warning(f"Ligne {line_number} ignorée : {error_details}")
                            if verbosity >= 1:
                                self.stdout.write(self.style.WARNING(f"Ligne {line_number} ignorée : {error_details}"))
                            continue
                        
                        # Traitement de la ligne si toutes les validations passent
                        try:
                            client, client_created = Client.objects.get_or_create(
                                email=client_email,
                                defaults={
                                    "shop": row['client_shop'].strip(), 
                                    "first_name": row.get('client_first_name', '').strip(), 
                                    "last_name": row.get('client_last_name', '').strip()
                                }
                            )
                            if client_created:
                                logger.debug(f"Ligne {line_number}: Client créé - {client_email}")
                            else:
                                logger.debug(f"Ligne {line_number}: Client existant - {client_email}")
                            
                            user_client, user_created = UserClient.objects.get_or_create(
                                email=user_email,
                                from_client=client,
                                defaults={
                                    "name": row.get('user_name', '').strip(),
                                    "last_name": row.get('user_last_name', '').strip(),
                                    "location": row.get('user_location', '').strip(),
                                    "from_client": client
                                }
                            )
                            if user_created:
                                logger.debug(f"Ligne {line_number}: UserClient créé - {user_email}")
                            
                            order, order_created = Order.objects.get_or_create(
                                order_id=row['order_id'].strip(),
                                from_client=client,
                                defaults={
                                    "product_id": product_ids,
                                    "customer_email": user_email,
                                    "customer_name": row.get('user_name', '').strip(),
                                    "mail_sent": False,
                                    "mail_sent_at": None
                                }
                            )
                            if order_created:
                                logger.debug(f"Ligne {line_number}: Commande créée - {order.order_id}")
                            
                            success_count += 1
                            logger.info(f"Ligne {line_number}: Traitement réussi - Order {order.order_id} pour client {client.email}")
                            
                            if verbosity >= 2:
                                self.stdout.write(f"Traitement : {order.order_id} pour {client.email}")
                        
                        except IntegrityError as e:
                            error_msg = f"Ligne {line_number}: Erreur d'intégrité de base de données : {str(e)}"
                            logger.error(error_msg, exc_info=True)
                            errors.append(error_msg)
                            skipped_count += 1
                            if verbosity >= 1:
                                self.stdout.write(self.style.ERROR(error_msg))
                        
                        except Exception as e:
                            error_msg = f"Ligne {line_number}: Erreur inattendue : {str(e)}"
                            logger.error(error_msg, exc_info=True)
                            errors.append(error_msg)
                            skipped_count += 1
                            if verbosity >= 1:
                                self.stdout.write(self.style.ERROR(error_msg))

                if dry_run:
                    logger.info("Dry-run: Rollback de la transaction")
                    raise Exception("DryRunRollback")
                else:
                    # Afficher le résumé
                    logger.info(f"Import terminé - Succès: {success_count}, Ignorées: {skipped_count}, Erreurs: {len(errors)}")
                    self.stdout.write(self.style.SUCCESS("\n" + "="*60))
                    self.stdout.write(self.style.SUCCESS("Résumé de l'import :"))
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Lignes traitées avec succès : {success_count}"))
                    if skipped_count > 0:
                        logger.warning(f"{skipped_count} ligne(s) ignorée(s) lors de l'import")
                        self.stdout.write(self.style.WARNING(f"  ⚠ Lignes ignorées : {skipped_count}"))
                    if errors:
                        logger.error(f"{len(errors)} erreur(s) rencontrée(s) lors de l'import")
                        self.stdout.write(self.style.ERROR(f"  ✗ Erreurs rencontrées : {len(errors)}"))
                    self.stdout.write(self.style.SUCCESS("="*60))
                    
                    if errors and verbosity >= 1:
                        self.stdout.write(self.style.ERROR("\nDétails des erreurs :"))
                        for error in errors[:20]:  # Limiter à 20 erreurs pour la lisibilité
                            self.stdout.write(self.style.ERROR(f"  - {error}"))
                        if len(errors) > 20:
                            self.stdout.write(self.style.ERROR(f"  ... et {len(errors) - 20} erreur(s) supplémentaire(s)"))
                    
                    if success_count > 0:
                        logger.info("Import terminé avec succès")
                        self.stdout.write(self.style.SUCCESS("\nImport terminé avec succès ! 🚀"))
                    elif skipped_count > 0:
                        logger.warning("Aucune ligne n'a pu être importée")
                        self.stdout.write(self.style.WARNING("\nAucune ligne n'a pu être importée. Vérifiez les erreurs ci-dessus."))

        except FileNotFoundError:
            error_msg = f"Le fichier '{file_path}' est introuvable."
            logger.error(error_msg)
            self.stdout.write(self.style.ERROR(f"Erreur : {error_msg}"))
        except PermissionError:
            error_msg = f"Permission refusée pour lire le fichier '{file_path}'."
            logger.error(error_msg)
            self.stdout.write(self.style.ERROR(f"Erreur : {error_msg}"))
        except UnicodeDecodeError as e:
            error_msg = f"Impossible de décoder le fichier. Vérifiez l'encodage (UTF-8 attendu). {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.stdout.write(self.style.ERROR(f"Erreur : {error_msg}"))
        except Exception as e:
            if str(e) == "DryRunRollback":
                # Afficher le résumé même en dry-run
                logger.info(f"Simulation terminée - Succès: {success_count}, Ignorées: {skipped_count}, Erreurs: {len(errors)}")
                self.stdout.write(self.style.SUCCESS("\n" + "="*60))
                self.stdout.write(self.style.SUCCESS("Résumé de la simulation :"))
                self.stdout.write(self.style.SUCCESS(f"  ✓ Lignes qui auraient été traitées : {success_count}"))
                if skipped_count > 0:
                    self.stdout.write(self.style.WARNING(f"  ⚠ Lignes qui auraient été ignorées : {skipped_count}"))
                if errors:
                    self.stdout.write(self.style.ERROR(f"  ✗ Erreurs rencontrées : {len(errors)}"))
                self.stdout.write(self.style.SUCCESS("="*60))
                self.stdout.write(self.style.SUCCESS("\nSimulation terminée. La base de données est restée intacte. 🧹"))
            else:
                error_msg = f"Une erreur inattendue est survenue : {e}"
                logger.exception(error_msg)
                self.stdout.write(self.style.ERROR(error_msg))
                if verbosity >= 2:
                    import traceback
                    self.stdout.write(self.style.ERROR(traceback.format_exc()))
                raise e