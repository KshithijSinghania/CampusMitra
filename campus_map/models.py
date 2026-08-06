from django.db import models


class Location(models.Model):
    CATEGORY_CHOICES = [
        ("academic", "Academic Building"),
        ("hostel", "Hostel"),
        ("mess", "Mess/Dining"),
        ("admin", "Administrative Office"),
        ("sports", "Sports Facility"),
        ("other", "Other"),
    ]

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other")
    latitude = models.FloatField()
    longitude = models.FloatField()
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name