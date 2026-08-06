from django.db import models
from django.contrib.auth.models import User
from django_cryptography.fields import encrypt


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    roll_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    hostel = models.CharField(max_length=50, blank=True)

    gmail_linked = models.BooleanField(default=False)
    gmail_refresh_token = encrypt(models.TextField(blank=True, default=""))
    gmail_history_id = models.CharField(max_length=32, blank=True, default="")
    gmail_watch_expiration = models.DateTimeField(null=True, blank=True)

    EMBEDDING_STATUS = [
        ("not_started", "Not started"),
        ("in_progress", "In progress"),
        ("ready", "Ready"),
        ("error", "Error"),
    ]
    embedding_status = models.CharField(max_length=20, choices=EMBEDDING_STATUS, default="not_started")
    embedding_total_messages = models.IntegerField(default=0)
    embedding_processed_messages = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} ({self.roll_number})"