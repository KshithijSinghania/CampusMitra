from django.db import models


class MessTiming(models.Model):
    MEAL_CHOICES = [
        ("breakfast", "Breakfast"),
        ("lunch", "Lunch"),
        ("snacks", "Snacks"),
        ("dinner", "Dinner"),
    ]

    hall = models.CharField(max_length=50)
    meal = models.CharField(max_length=20, choices=MEAL_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        unique_together = ["hall", "meal"]  # one row per hall+meal combination, not duplicates

    def __str__(self):
        return f"{self.hall} — {self.get_meal_display()}: {self.start_time}–{self.end_time}"


class Contact(models.Model):
    department = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    designation = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.department})"

class HumanEscalation(models.Model):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, null=True, blank=True)
    question = models.TextField()
    last_generation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.question[:50]}... ({'resolved' if self.resolved else 'open'})"