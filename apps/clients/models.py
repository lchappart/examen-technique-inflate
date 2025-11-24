from django.db import models
from apps.common.models import BaseModel


class Client(BaseModel):
    email = models.EmailField(unique=True, null=True)
    shop = models.CharField(max_length=255, unique=True, null=True)
    first_name = models.CharField(max_length=50, default="")
    last_name = models.CharField(max_length=50, default="")
    is_active = models.BooleanField(default=True)


class UserClient(BaseModel):
    name = models.CharField(max_length=255, null = True)
    last_name = models.CharField(max_length=255, null = True)
    email = models.EmailField(unique=False, null=True)
    location = models.CharField(max_length=255, null = True)
    from_client = models.ForeignKey(
        Client, 
        on_delete=models.CASCADE, 
        null = True,
        blank = True,
        related_name = "users"
    )