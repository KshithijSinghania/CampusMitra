from celery import shared_task
from .gmail_ingest import backfill_user_mailbox as _backfill


@shared_task
def backfill_user_mailbox_task(user_id):
    _backfill(user_id)