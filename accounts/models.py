from django.db import models
from django.contrib.auth.models import User
from django_cryptography.fields import encrypt


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    roll_number = models.CharField(max_length=20, unique=False)
    hostel = models.CharField(max_length=50, blank=True)

    # Gmail linkage (Phase 2.5)
    gmail_linked = models.BooleanField(default=False)
    gmail_refresh_token = encrypt(models.TextField(blank=True, default=""))
    gmail_history_id = models.CharField(max_length=32, blank=True, default="")

    def __str__(self):
        return f"{self.user.username} ({self.roll_number})"