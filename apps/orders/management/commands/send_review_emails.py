from django.core.management.base import BaseCommand
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from apps.orders.models import Order
from apps.orders.utils import send_review_request_email
from django.utils import timezone
from tqdm import tqdm
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Envoie les emails de demande d\'avis aux clients pour les commandes non traitées'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simule l\'envoi sans réellement envoyer les emails ni mettre à jour la base de données'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limite le nombre d\'emails à envoyer (utile pour les tests)'
        )

    def handle(self, *args, **options): #Gère l'envoi des emails de demande de revue
        dry_run = options['dry_run']
        limit = options['limit']
        verbosity = options['verbosity']
        
        logger.info("Démarrage de l'envoi des emails de demande d'avis")
        self.stdout.write(self.style.SUCCESS("Démarrage de l'envoi des emails de demande d'avis..."))
        
        if dry_run:
            logger.warning("Mode Dry-Run activé. Aucun email ne sera envoyé et aucune modification ne sera sauvegardée.")
            self.stdout.write(self.style.WARNING("Mode Dry-Run activé. Aucun email ne sera envoyé. 🛡️"))
        
        # Récupérer les commandes non traitées
        orders_queryset = Order.objects.filter(mail_sent=False)
        total_orders = orders_queryset.count()
        
        if total_orders == 0:
            logger.info("Aucune commande en attente d'envoi d'email")
            self.stdout.write(self.style.SUCCESS("Aucune commande en attente d'envoi d'email."))
            return
        
        if limit:
            orders_queryset = orders_queryset[:limit]
            total_orders = min(total_orders, limit)
            logger.info(f"Limite de {limit} commande(s) appliquée")
            self.stdout.write(self.style.WARNING(f"Limite de {limit} commande(s) appliquée"))
        
        logger.info(f"{total_orders} commande(s) à traiter")
        self.stdout.write(self.style.SUCCESS(f"{total_orders} commande(s) à traiter"))
        
        success_count = 0
        failed_count = 0
        skipped_count = 0
        errors = []
        
        try:
            with transaction.atomic():
                for order in tqdm(orders_queryset, total=total_orders, desc="Envoi des emails"):
                    # Validation préalable de l'email
                    if not order.customer_email:
                        error_msg = f"Commande {order.order_id or order.pk}: Email client vide"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        skipped_count += 1
                        if verbosity >= 1:
                            self.stdout.write(self.style.WARNING(error_msg))
                        continue
                    
                    try:
                        validate_email(order.customer_email)
                    except ValidationError:
                        error_msg = f"Commande {order.order_id or order.pk}: Email invalide '{order.customer_email}'"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        skipped_count += 1
                        if verbosity >= 1:
                            self.stdout.write(self.style.WARNING(error_msg))
                        continue
                    
                    # Validation que la commande a un order_id
                    if not order.order_id:
                        error_msg = f"Commande ID {order.pk}: order_id est vide"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        skipped_count += 1
                        if verbosity >= 1:
                            self.stdout.write(self.style.WARNING(error_msg))
                        continue
                    
                    # Validation que la commande a un client associé
                    if not order.from_client:
                        error_msg = f"Commande {order.order_id}: Aucun client associé"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        skipped_count += 1
                        if verbosity >= 1:
                            self.stdout.write(self.style.WARNING(error_msg))
                        continue
                    
                    # Envoi de l'email (ou simulation en dry-run)
                    if dry_run:
                        logger.debug(f"[DRY-RUN] Email serait envoyé pour la commande {order.order_id} à {order.customer_email}")
                        if verbosity >= 2:
                            self.stdout.write(f"[DRY-RUN] Email serait envoyé pour la commande {order.order_id} à {order.customer_email}")
                        success_count += 1
                    else:
                        if send_review_request_email(order):
                            try:
                                order.mail_sent = True
                                order.mail_sent_at = timezone.now()
                                order.save()
                                success_count += 1
                                logger.info(f"Email envoyé avec succès pour la commande {order.order_id} à {order.customer_email}")
                                if verbosity >= 2:
                                    self.stdout.write(self.style.SUCCESS(f"✓ Email envoyé à {order.customer_email} (Commande {order.order_id})"))
                            except IntegrityError as e:
                                error_msg = f"Commande {order.order_id}: Erreur lors de la sauvegarde - {str(e)}"
                                logger.error(error_msg, exc_info=True)
                                errors.append(error_msg)
                                failed_count += 1
                                if verbosity >= 1:
                                    self.stdout.write(self.style.ERROR(error_msg))
                            except Exception as e:
                                error_msg = f"Commande {order.order_id}: Erreur inattendue lors de la sauvegarde - {str(e)}"
                                logger.error(error_msg, exc_info=True)
                                errors.append(error_msg)
                                failed_count += 1
                                if verbosity >= 1:
                                    self.stdout.write(self.style.ERROR(error_msg))
                        else:
                            failed_count += 1
                            error_msg = f"Échec de l'envoi pour la commande {order.order_id} à {order.customer_email}"
                            logger.warning(error_msg)
                            errors.append(error_msg)
                            if verbosity >= 1:
                                self.stdout.write(self.style.ERROR(f"✗ Échec pour {order.customer_email} (Commande {order.order_id})"))
                
                if dry_run:
                    raise Exception("DryRunRollback")
                else:
                    # Afficher le résumé
                    logger.info(f"Envoi terminé - Succès: {success_count}, Échecs: {failed_count}, Ignorées: {skipped_count}")
                    self.stdout.write(self.style.SUCCESS("\n" + "="*60))
                    self.stdout.write(self.style.SUCCESS("Résumé de l'envoi :"))
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Emails envoyés avec succès : {success_count}"))
                    if failed_count > 0:
                        self.stdout.write(self.style.ERROR(f"  ✗ Échecs d'envoi : {failed_count}"))
                    if skipped_count > 0:
                        self.stdout.write(self.style.WARNING(f"  ⚠ Commandes ignorées : {skipped_count}"))
                    self.stdout.write(self.style.SUCCESS("="*60))
                    
                    if errors and verbosity >= 1:
                        self.stdout.write(self.style.ERROR("\nDétails des erreurs :"))
                        for error in errors[:20]:  # Limiter à 20 erreurs pour la lisibilité
                            self.stdout.write(self.style.ERROR(f"  - {error}"))
                        if len(errors) > 20:
                            self.stdout.write(self.style.ERROR(f"  ... et {len(errors) - 20} erreur(s) supplémentaire(s)"))
                    
                    if success_count > 0:
                        logger.info("Envoi des emails terminé avec succès")
                        self.stdout.write(self.style.SUCCESS("\nEnvoi des emails terminé ! 📧"))
                    elif failed_count > 0 or skipped_count > 0:
                        logger.warning("Aucun email n'a pu être envoyé. Vérifiez les erreurs ci-dessus.")
                        self.stdout.write(self.style.WARNING("\nAucun email n'a pu être envoyé. Vérifiez les erreurs ci-dessus."))
        
        except Exception as e:
            if str(e) == "DryRunRollback":
                # Afficher le résumé même en dry-run
                logger.info(f"Simulation terminée - Succès: {success_count}, Échecs: {failed_count}, Ignorées: {skipped_count}")
                self.stdout.write(self.style.SUCCESS("\n" + "="*60))
                self.stdout.write(self.style.SUCCESS("Résumé de la simulation :"))
                self.stdout.write(self.style.SUCCESS(f"  ✓ Emails qui auraient été envoyés : {success_count}"))
                if failed_count > 0:
                    self.stdout.write(self.style.ERROR(f"  ✗ Échecs qui auraient eu lieu : {failed_count}"))
                if skipped_count > 0:
                    self.stdout.write(self.style.WARNING(f"  ⚠ Commandes qui auraient été ignorées : {skipped_count}"))
                self.stdout.write(self.style.SUCCESS("="*60))
                self.stdout.write(self.style.SUCCESS("\nSimulation terminée. Aucun email n'a été envoyé. 🧹"))
            else:
                error_msg = f"Une erreur inattendue est survenue : {e}"
                logger.exception(error_msg)
                self.stdout.write(self.style.ERROR(error_msg))
                if verbosity >= 2:
                    import traceback
                    self.stdout.write(self.style.ERROR(traceback.format_exc()))
                raise e