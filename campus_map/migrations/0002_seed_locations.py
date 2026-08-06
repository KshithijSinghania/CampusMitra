from django.db import migrations


def add_locations(apps, schema_editor):
    Location = apps.get_model("campus_map", "Location")
    Location.objects.bulk_create([
        Location(name="Main Building", category="academic", latitude=22.5192, longitude=75.9199, description="Central academic building"),
        Location(name="Library", category="academic", latitude=22.5195, longitude=75.9205, description="Central library"),
        Location(name="Hostel H10", category="hostel", latitude=22.5180, longitude=75.9190, description="Boys hostel H10"),
        Location(name="Mess Hall A", category="mess", latitude=22.5188, longitude=75.9195, description="Main mess hall"),
        Location(name="Sports Complex", category="sports", latitude=22.5170, longitude=75.9210, description="Gym and outdoor sports facilities"),
    ])


def remove_locations(apps, schema_editor):
    Location = apps.get_model("campus_map", "Location")
    Location.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("campus_map", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_locations, remove_locations),
    ]