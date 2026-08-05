from django.db import models
from django.contrib.auth.models import User


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    full_name = models.CharField(max_length=100, blank=True)
    roll_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True)
    year = models.PositiveSmallIntegerField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.user.username