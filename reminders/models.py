from django.db import models
from django.contrib.auth.models import User


class Reminder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reminders")
    text = models.CharField(max_length=255)
    remind_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["remind_at"]  # soonest reminders show first by default

    def __str__(self):
        return f"{self.text} ({self.remind_at})"