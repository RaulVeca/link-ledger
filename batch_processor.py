import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from django.db import transaction

from file_handler.models import Document, Invoice, ProcessingJob
from file_handler.services.invoice_extractor import InvoiceExtractor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BatchInvoiceProcessor:
    """Process multiple invoice OCR files in batch"""
    
    def __init__(self, source_dir: str = None, bucket_name: str = 'invoices'):
        self.source_dir = source_dir or 'ocr_output'
        self.bucket_name = bucket_name
        self.results = {
            'successful': [],
            'failed': [],
            'skipped': [],
            'total': 0
        }
    
    def process_directory(self, directory_path: str = None) -> Dict:
        """Process all JSON files in a directory"""
        dir_path = Path(directory_path or self.source_dir)
        
        if not dir_path.exists():
            raise ValueError(f"Directory {dir_path} does not exist")
        
        json_files = list(dir_path.glob('*.json'))
        logger.info(f"Found {len(json_files)} JSON files to process")
        
        self.results['total'] = len(json_files)
        
        for json_file in json_files:
            self.process_single_file(str(json_file))
        
        self._print_summary()
        return self.results
    
    def process_file_list(self, file_paths: List[str]) -> Dict:
        """Process a specific list of files"""
        self.results['total'] = len(file_paths)
        
        for file_path in file_paths:
            self.process_single_file(file_path)
        
        self._print_summary()
        return self.results
    
    @transaction.atomic
    def process_single_file(self, file_path: str) -> bool:
        """Process a single OCR JSON file"""
        file_path = Path(file_path)
        logger.info(f"Processing: {file_path.name}")
        
        try:
            # Load OCR data
            with open(file_path, 'r', encoding='utf-8') as f:
                ocr_data = json.load(f)
            
            # Get original filename from metadata
            original_filename = ocr_data.get('metadata', {}).get('original_filename', file_path.stem)
            
            # Check if already processed
            existing_doc = Document.objects.filter(
                filename=original_filename,
                status='completed'
            ).first()
            
            if existing_doc:
                logger.warning(f"  ⚠ Already processed: {original_filename}")
                self.results['skipped'].append({
                    'file': file_path.name,
                    'reason': 'Already processed'
                })
                return False
            
            # Create document record
            document = Document.objects.create(
                filename=original_filename,
                bucket_name=self.bucket_name,
                file_path=str(file_path),
                status='processing',
                processing_started=datetime.now()
            )
            
            # Create processing job
            job = ProcessingJob.objects.create(
                document=document
            )
            
            # Extract invoice data
            extractor = InvoiceExtractor(ocr_data)
            
            # Check if we can find an invoice number
            invoice_number = extractor.find_invoice_number()
            if not invoice_number:
                raise ValueError("No invoice number found")
            
            # Process the invoice
            invoice = extractor.process_invoice(document)
            
            # Update document status
            document.status = 'completed'
            document.processing_completed = datetime.now()
            document.save()
            
            # Update job
            job.success = True
            job.completed_at = datetime.now()
            job.pages_processed = len(ocr_data.get('pages', []))
            job.save()
            
            logger.info(f"  ✓ Success: Invoice {invoice.invoice_number} - €{invoice.total_amount}")
            
            self.results['successful'].append({
                'file': file_path.name,
                'invoice_number': invoice.invoice_number,
                'total': float(invoice.total_amount),
                'supplier': invoice.supplier.name,
                'customer': invoice.customer.name
            })
            
            return True
            
        except Exception as e:
            logger.error(f"  ✗ Failed: {str(e)}")
            
            # Update document status if it exists
            if 'document' in locals():
                document.status = 'failed'
                document.error_message = str(e)
                document.processing_completed = datetime.now()
                document.save()
            
            # Update job if it exists
            if 'job' in locals():
                job.success = False
                job.error_details = str(e)
                job.completed_at = datetime.now()
                job.save()
            
            self.results['failed'].append({
                'file': file_path.name,
                'error': str(e)
            })
            
            return False
    
    def _print_summary(self):
        """Print processing summary"""
        print("\n" + "=" * 60)
        print("BATCH PROCESSING SUMMARY")
        print("=" * 60)
        print(f"Total files: {self.results['total']}")
        print(f"✓ Successful: {len(self.results['successful'])}")
        print(f"⚠ Skipped: {len(self.results['skipped'])}")
        print(f"✗ Failed: {len(self.results['failed'])}")
        
        if self.results['successful']:
            print("\nSuccessfully processed:")
            for item in self.results['successful']:
                print(f"  - {item['invoice_number']}: €{item['total']:.2f} ({item['supplier']})")
        
        if self.results['failed']:
            print("\nFailed to process:")
            for item in self.results['failed']:
                print(f"  - {item['file']}: {item['error']}")
        
        if self.results['skipped']:
            print("\nSkipped files:")
            for item in self.results['skipped']:
                print(f"  - {item['file']}: {item['reason']}")
        
        # Calculate totals
        if self.results['successful']:
            total_amount = sum(item['total'] for item in self.results['successful'])
            print(f"\nTotal invoice amount processed: €{total_amount:.2f}")


class InvoiceReprocessor:
    """Reprocess failed invoices"""
    
    @staticmethod
    def reprocess_failed():
        """Find and reprocess all failed documents"""
        failed_docs = Document.objects.filter(status='failed')
        logger.info(f"Found {failed_docs.count()} failed documents to reprocess")
        
        processor = BatchInvoiceProcessor()
        file_paths = [doc.file_path for doc in failed_docs]
        
        return processor.process_file_list(file_paths)
    
    @staticmethod
    def reprocess_document(document_id):
        """Reprocess a specific document"""
        document = Document.objects.get(id=document_id)
        processor = BatchInvoiceProcessor()
        return processor.process_single_file(document.file_path)