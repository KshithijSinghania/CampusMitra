from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb
import cohere
import base64
from django.conf import settings


def get_gmail_service(profile):
    creds = Credentials(
        token=None,
        refresh_token=profile.gmail_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
        client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
    )
    return build("gmail", "v1", credentials=creds)


def extract_plain_text(payload):
    """Pulls readable text out of a Gmail message payload, handling both plain and HTML parts."""
    parts = payload.get("parts", [payload])
    text_content = ""
    for part in parts:
        mime_type = part.get("mimeType", "")
        body_data = part.get("body", {}).get("data")
        if not body_data:
            continue
        decoded = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
        if mime_type == "text/plain":
            text_content += decoded
        elif mime_type == "text/html":
            text_content += BeautifulSoup(decoded, "html.parser").get_text()
    return text_content.strip()


def backfill_user_mailbox(user_id):
    from accounts.models import StudentProfile  # imported here to avoid circular imports

    profile = StudentProfile.objects.get(user_id=user_id)
    profile.embedding_status = "in_progress"
    profile.save()

    try:
        service = get_gmail_service(profile)
        co = cohere.Client(settings.COHERE_API_KEY)
        chroma_client = chromadb.PersistentClient(path="vectorstore")
        collection = chroma_client.get_or_create_collection(name=f"gmail_{user_id}")

        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

        # Step 1: list message IDs (limited to last 200 for a manageable first backfill)
        results = service.users().messages().list(userId="me", maxResults=200).execute()
        messages = results.get("messages", [])
        profile.embedding_total_messages = len(messages)
        profile.save()

        for i, msg_ref in enumerate(messages):
            msg = service.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute()
            headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
            text = extract_plain_text(msg["payload"])

            if text:
                chunks = splitter.split_text(text)
                if chunks:
                    embeddings = co.embed(texts=chunks, model="embed-english-v3.0", input_type="search_document").embeddings
                    collection.upsert(
                        ids=[f"{msg_ref['id']}_{idx}" for idx in range(len(chunks))],
                        embeddings=embeddings,
                        documents=chunks,
                        metadatas=[{
                            "user_id": user_id,
                            "message_id": msg_ref["id"],
                            "sender": headers.get("From", ""),
                            "subject": headers.get("Subject", ""),
                            "date": headers.get("Date", ""),
                            "source": "gmail",
                            "chunk_index": idx,
                        } for idx in range(len(chunks))],
                    )

            profile.embedding_processed_messages = i + 1
            profile.save()

        # record historyId so Phase 2.5.4's incremental sync knows where to resume from
        profile_data = service.users().getProfile(userId="me").execute()
        profile.gmail_history_id = str(profile_data.get("historyId", ""))
        profile.embedding_status = "ready"
        profile.save()

    except Exception as e:
        profile.embedding_status = "error"
        profile.save()
        raise e