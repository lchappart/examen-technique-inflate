from django.db import models
from apps.common.models import BaseModel
from apps.clients.models import Client

class Order(BaseModel):
    order_id = models.CharField(max_length=255, null = True, blank = True)
    product_id = models.JSONField(null = True, blank = True)
    customer_email = models.EmailField(null = True, blank = True)
    customer_name = models.CharField(max_length=255, null = True, blank = True)
    from_client = models.ForeignKey(
        Client, 
        on_delete=models.CASCADE, 
        null = True,
        blank = True,
        related_name = "orders"
    )
    mail_sent = models.BooleanField(default=False)
    mail_sent_at = models.DateTimeField(null = True, blank = True)