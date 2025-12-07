"""
Django management command to ingest PDF documents into Pinecone.

Usage:
    python manage.py ingest_documents /path/to/pdfs
    python manage.py ingest_documents --single /path/to/file.pdf
"""
import os
from django.core.management.base import BaseCommand, CommandError
from apps.rag.services import DocumentProcessor
from apps.rag.models import Document


class Command(BaseCommand):
    help = 'Ingest PDF documents into Pinecone vector database'

    def add_arguments(self, parser):
        parser.add_argument(
            'path',
            type=str,
            help='Path to PDF file or directory containing PDFs'
        )
        parser.add_argument(
            '--single',
            action='store_true',
            help='Process a single PDF file instead of a directory'
        )
        parser.add_argument(
            '--reprocess',
            action='store_true',
            help='Reprocess documents that have already been ingested'
        )

    def handle(self, *args, **options):
        path = options['path']
        is_single = options['single']
        reprocess = options['reprocess']

        if not os.path.exists(path):
            raise CommandError(f"Path not found: {path}")

        processor = DocumentProcessor()

        if is_single:
            if not path.endswith('.pdf'):
                raise CommandError("File must be a PDF")
            
            self.stdout.write(f"Processing single file: {path}")
            doc = processor.process_document(path)
            
            if doc.status == 'completed':
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ {doc.filename}: {doc.total_chunks} chunks, {doc.total_pages} pages"
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"✗ {doc.filename}: {doc.error_message}")
                )
        else:
            self.stdout.write(f"Processing directory: {path}")
            
            results = processor.process_directory(path)
            
            self.stdout.write("\n" + "="*50)
            self.stdout.write(f"Total files: {results['total']}")
            self.stdout.write(
                self.style.SUCCESS(f"Successful: {results['successful']}")
            )
            if results['failed'] > 0:
                self.stdout.write(
                    self.style.ERROR(f"Failed: {results['failed']}")
                )
            
            self.stdout.write("\nDetails:")
            for doc in results['documents']:
                if doc['status'] == 'completed':
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ {doc['filename']}: {doc['chunks']} chunks")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ {doc['filename']}: {doc['status']}")
                    )
