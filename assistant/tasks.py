from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from .gmail_ingest import backfill_user_mailbox as _backfill
from .gmail_ingest import incremental_sync_user_mailbox as _incremental_sync
from .gmail_ingest import register_gmail_watch


@shared_task
def backfill_user_mailbox_task(user_id):
    _backfill(user_id)


@shared_task
def incremental_sync_task(user_id):
    _incremental_sync(user_id)


@shared_task
def renew_expiring_watches():
    from accounts.models import StudentProfile  # imported here to avoid circular imports

    soon = timezone.now() + timedelta(hours=24)
    expiring_profiles = StudentProfile.objects.filter(
        gmail_linked=True,
        gmail_watch_expiration__lte=soon,
    )
    for profile in expiring_profiles:
        register_gmail_watch(profile)