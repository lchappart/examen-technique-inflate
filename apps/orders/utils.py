from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.template.exceptions import TemplateDoesNotExist, TemplateSyntaxError
from apps.orders.models import Order
import logging

logger = logging.getLogger(__name__)

def send_review_request_email(order: Order):
    """
    Envoie un email de demande d'avis pour une commande.
    
    Args:
        order: Instance de Order pour laquelle envoyer l'email
        
    Returns:
        bool: True si l'email a été envoyé avec succès, False sinon
    """
    # Validation de l'email du client
    if not order.customer_email:
        logger.error(f"Order {order.order_id}: customer_email est vide")
        return False
    
    try:
        validate_email(order.customer_email)
    except ValidationError as e:
        logger.error(f"Order {order.order_id}: Email invalide '{order.customer_email}': {e}")
        return False
    
    # Validation que la commande a un order_id
    if not order.order_id:
        logger.error(f"Order ID {order.pk}: order_id est vide")
        return False
    
    # Validation que la commande a un client associé
    if not order.from_client:
        logger.error(f"Order {order.order_id}: Aucun client associé (from_client est None)")
        return False
    
    try:
        # Rendu du template HTML
        try:
            html_message = render_to_string('orders/review_request.html', {'order': order})
        except TemplateDoesNotExist:
            logger.error(f"Order {order.order_id}: Template 'orders/review_request.html' introuvable")
            return False
        except TemplateSyntaxError as e:
            logger.error(f"Order {order.order_id}: Erreur de syntaxe dans le template: {e}")
            return False
        
        # Création du message texte simple (fallback)
        customer_name = order.customer_name or "Client"
        shop_name = order.from_client.shop if order.from_client else "notre boutique"
        products_list = ""
        if order.product_id and isinstance(order.product_id, list):
            products_list = "\n".join([f"- Produit référence : {product}" for product in order.product_id])
        
        plain_message = f"""Bonjour {customer_name},

Merci pour votre commande {order.order_id} chez {shop_name}.

Nous espérons que vous avez apprécié vos produits :
{products_list}

Pourriez-vous prendre un instant pour partager votre expérience ?
"""
        
        # Envoi de l'email
        send_mail(
            subject=f"Partagez votre avis sur votre commande {order.order_id}",
            message=plain_message,
            from_email="noreply@inflate.review",
            recipient_list=[order.customer_email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Email de demande d'avis envoyé avec succès pour la commande {order.order_id} à {order.customer_email}")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email pour la commande {order.order_id} à {order.customer_email}: {e}", exc_info=True)
        return False