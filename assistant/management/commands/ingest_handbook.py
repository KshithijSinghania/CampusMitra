from django.core.management.base import BaseCommand
from assistant.ingestion import ingest_handbook_docs


class Command(BaseCommand):
    help = "Chunks and embeds all placeholder/real FAQ documents into the institutional_knowledge Chroma collection."

    def handle(self, *args, **options):
        ingest_handbook_docs()
        self.stdout.write(self.style.SUCCESS("Handbook ingestion complete."))