from django.core.management.base import BaseCommand
from apps.orders.models import Order
from apps.orders.utils import send_review_request_email
from django.utils import timezone

class Command(BaseCommand):
    help = 'Send review request emails to customers'

    def handle(self, *args, **kwargs):
        for order in Order.objects.filter(mail_sent=False):
            if send_review_request_email(order):
                order.mail_sent = True
                order.mail_sent_at = timezone.now()
                order.save()
                self.stdout.write(self.style.SUCCESS(f"Review request email sent to {order.customer_email}"))
            else:
                self.stdout.write(self.style.ERROR(f"Failed to send review request email to {order.customer_email}"))