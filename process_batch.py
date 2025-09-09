from django.core.management.base import BaseCommand
from file_handler.services.batch_processor import BatchInvoiceProcessor, InvoiceReprocessor
from pathlib import Path


class Command(BaseCommand):
    help = 'Process multiple invoice OCR files in batch'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dir',
            type=str,
            help='Directory containing OCR JSON files',
            default='ocr_output'
        )
        parser.add_argument(
            '--files',
            nargs='+',
            help='Specific files to process'
        )
        parser.add_argument(
            '--reprocess-failed',
            action='store_true',
            help='Reprocess all failed documents'
        )
    
    def handle(self, *args, **options):
        processor = BatchInvoiceProcessor()
        
        if options['reprocess_failed']:
            self.stdout.write("Reprocessing failed documents...")
            results = InvoiceReprocessor.reprocess_failed()
        elif options['files']:
            self.stdout.write(f"Processing {len(options['files'])} files...")
            results = processor.process_file_list(options['files'])
        else:
            directory = options['dir']
            self.stdout.write(f"Processing directory: {directory}")
            results = processor.process_directory(directory)
        
        # Print results
        success_rate = (len(results['successful']) / results['total'] * 100) if results['total'] > 0 else 0
        self.stdout.write(
            self.style.SUCCESS(f"\nSuccess rate: {success_rate:.1f}%")
        )