"""
Document processor for PDF ingestion and chunking.
"""
import os
import uuid
import logging
from typing import List, Dict, Any
from pathlib import Path

from django.conf import settings
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..models import Document, DocumentChunk
from .vector_store import VectorStoreService

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Processes PDF documents for RAG:
    1. Extracts text from PDFs
    2. Splits into chunks
    3. Generates embeddings
    4. Stores in Pinecone
    """
    
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        self.vector_store = VectorStoreService()
    
    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text from PDF file."""
        try:
            reader = PdfReader(pdf_path)
            pages = []
            full_text = ""
            
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages.append({
                    'page_number': i + 1,
                    'text': text
                })
                full_text += text + "\n\n"
            
            return {
                'full_text': full_text.strip(),
                'pages': pages,
                'num_pages': len(reader.pages),
                'success': True
            }
        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path}: {e}")
            return {
                'full_text': '',
                'pages': [],
                'num_pages': 0,
                'success': False,
                'error': str(e)
            }
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks for embedding."""
        if not text.strip():
            return []
        return self.text_splitter.split_text(text)
    
    def process_document(self, pdf_path: str) -> Document:
        """
        Process a single PDF document:
        1. Extract text
        2. Create chunks
        3. Generate embeddings and store in Pinecone
        4. Save to database
        """
        filename = os.path.basename(pdf_path)
        file_size = os.path.getsize(pdf_path)
        
        # Create or get document record
        document, created = Document.objects.update_or_create(
            filename=filename,
            defaults={
                'file_path': pdf_path,
                'file_size_bytes': file_size,
                'status': 'processing'
            }
        )
        
        try:
            # Extract text
            logger.info(f"Extracting text from {filename}")
            result = self.extract_text_from_pdf(pdf_path)
            
            if not result['success']:
                document.status = 'failed'
                document.error_message = result.get('error', 'Unknown error')
                document.save()
                return document
            
            document.total_pages = result['num_pages']
            
            # Chunk text
            chunks = self.chunk_text(result['full_text'])
            logger.info(f"Created {len(chunks)} chunks from {filename}")
            
            if not chunks:
                document.status = 'failed'
                document.error_message = 'No text content extracted'
                document.save()
                return document
            
            # Delete existing chunks for this document
            DocumentChunk.objects.filter(document=document).delete()
            
            # Generate embeddings and store in Pinecone
            chunk_records = []
            vectors_to_upsert = []
            
            for i, chunk_text in enumerate(chunks):
                pinecone_id = f"{document.id}_{i}"
                
                # Prepare metadata for Pinecone
                metadata = {
                    'document_id': str(document.id),
                    'filename': filename,
                    'chunk_index': i,
                    'text': chunk_text[:1000],  # Pinecone metadata limit
                }
                
                vectors_to_upsert.append({
                    'id': pinecone_id,
                    'text': chunk_text,
                    'metadata': metadata
                })
                
                # Create DB record
                chunk_records.append(DocumentChunk(
                    document=document,
                    chunk_index=i,
                    pinecone_id=pinecone_id,
                    content_preview=chunk_text[:500],
                    token_count=len(chunk_text.split()),
                ))
            
            # Batch upsert to Pinecone
            self.vector_store.upsert_documents(vectors_to_upsert)
            
            # Bulk create chunk records
            DocumentChunk.objects.bulk_create(chunk_records)
            
            document.total_chunks = len(chunks)
            document.status = 'completed'
            document.error_message = ''
            document.save()
            
            logger.info(f"Successfully processed {filename}: {len(chunks)} chunks")
            return document
            
        except Exception as e:
            logger.error(f"Failed to process {filename}: {e}")
            document.status = 'failed'
            document.error_message = str(e)
            document.save()
            return document
    
    def process_directory(self, directory_path: str) -> Dict[str, Any]:
        """Process all PDF files in a directory."""
        path = Path(directory_path)
        
        if not path.exists():
            raise ValueError(f"Directory not found: {directory_path}")
        
        pdf_files = list(path.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files in {directory_path}")
        
        results = {
            'total': len(pdf_files),
            'successful': 0,
            'failed': 0,
            'documents': []
        }
        
        for pdf_file in pdf_files:
            doc = self.process_document(str(pdf_file))
            results['documents'].append({
                'filename': doc.filename,
                'status': doc.status,
                'chunks': doc.total_chunks
            })
            
            if doc.status == 'completed':
                results['successful'] += 1
            else:
                results['failed'] += 1
        
        return results
