from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import StudentProfile
from django.contrib.auth.signals import user_logged_out
from assistant.tasks import summarize_session


@receiver(post_save, sender=User)
def create_or_update_student_profile(sender, instance, created, **kwargs):
    if created:
        StudentProfile.objects.create(user=instance)



@receiver(user_logged_out)
def trigger_session_summary(sender, request, user, **kwargs):
    if user and request.session.session_key:
        summarize_session.delay(user.id, request.session.session_key)