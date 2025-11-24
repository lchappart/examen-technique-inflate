from django.core.mail import send_mail
from apps.orders.models import Order
from django.template.loader import render_to_string

def send_review_request_email(order: Order):
    try:
        html_message = render_to_string('orders/review_request.html', {'order': order})
        send_mail(
            subject=f"Partagez votre avis sur votre commande {order.order_id}",
            message="Bonjour <strong>{{ order.customer_name }}</strong>, Merci pour votre commande <strong>{{ order.order_id }}</strong> chez <em>{{ order.from_client.shop }}</em>. Nous espérons que vous avez apprécié vos produits : <ul> {% for product in order.product_id %} <li>Produit référence : {{ product }}</li> {% endfor %} </ul> Pourriez-vous prendre un instant pour partager votre expérience ?",
            from_email="noreply@inflate.review",
            recipient_list=[order.customer_email],
            html_message=html_message,
        )
        return True
    except Exception as e:
        print(f"Error sending review request mail: {e}")
        return False