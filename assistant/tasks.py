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

@shared_task
def summarize_session(user_id, session_id):
    from django.contrib.auth.models import User
    from .models import ConversationLog, SessionSummary
    import cohere
    from django.conf import settings

    logs = ConversationLog.objects.filter(user_id=user_id, session_id=session_id).order_by("timestamp")
    if not logs:
        return

    transcript = "\n\n".join(f"Q: {log.question}\nA: {log.answer}" for log in logs)

    co = cohere.ClientV2(api_key=settings.COHERE_API_KEY)
    response = co.chat(
        model="command-a-03-2025",
        messages=[
            {"role": "system", "content": (
                "Summarize this conversation between a student and a campus assistant "
                "chatbot in 2-3 sentences, capturing what topics were discussed and any "
                "important facts the student was told. This summary will be used as "
                "long-term memory context in future sessions."
            )},
            {"role": "user", "content": transcript},
        ],
        temperature=0.2,
    )

    SessionSummary.objects.create(
        user_id=user_id,
        summary_text=response.message.content[0].text.strip(),
    )