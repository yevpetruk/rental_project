from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    USER_TYPES = [
        ('tenant', 'Tenant'),
        ('landlord', 'Landlord'),
    ]

    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='tenant')
    phone = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"