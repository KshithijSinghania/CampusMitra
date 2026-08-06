from django.db import migrations
from datetime import time


def add_data(apps, schema_editor):
    MessTiming = apps.get_model("assistant", "MessTiming")
    Contact = apps.get_model("assistant", "Contact")

    MessTiming.objects.bulk_create([
        MessTiming(hall="Mess Hall A", meal="breakfast", start_time=time(7, 30), end_time=time(9, 30)),
        MessTiming(hall="Mess Hall A", meal="lunch", start_time=time(12, 0), end_time=time(14, 0)),
        MessTiming(hall="Mess Hall A", meal="snacks", start_time=time(17, 0), end_time=time(18, 0)),
        MessTiming(hall="Mess Hall A", meal="dinner", start_time=time(19, 30), end_time=time(21, 30)),
    ])

    Contact.objects.bulk_create([
        Contact(department="Academic Office", name="Placeholder Name", designation="Section Officer", phone="0731-2361XXX", email="academic@iiti.ac.in"),
        Contact(department="Hostel Office", name="Placeholder Name", designation="Warden", phone="0731-2361XXX", email="hostel@iiti.ac.in"),
    ])


def remove_data(apps, schema_editor):
    MessTiming = apps.get_model("assistant", "MessTiming")
    Contact = apps.get_model("assistant", "Contact")
    MessTiming.objects.all().delete()
    Contact.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_data, remove_data),
    ]