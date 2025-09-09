import os
import django
import shutil
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'link_ledger.settings')
django.setup()

from file_handler.services.batch_processor import BatchInvoiceProcessor
from file_handler.models import Invoice, Document

def setup_test_files():
    """Copy your OCR file multiple times to simulate batch"""
    test_dir = Path('test_batch')
    test_dir.mkdir(exist_ok=True)
    
    # Copy the Amazon invoice with different names
    source = Path('invoice_ocr.json')
    if source.exists():
        # Create copies simulating different invoices
        shutil.copy(source, test_dir / 'invoice_001.json')
        shutil.copy(source, test_dir / 'invoice_002.json')
        shutil.copy(source, test_dir / 'invoice_003.json')
        print(f"Created test files in {test_dir}")
    else:
        print("invoice_ocr.json not found!")
        return False
    return True

def run_batch_test():
    """Test batch processing"""
    print("=" * 60)
    print("BATCH PROCESSING TEST")
    print("=" * 60)
    
    # Setup test files
    if not setup_test_files():
        return
    
    # Initialize processor
    processor = BatchInvoiceProcessor(source_dir='test_batch')
    
    # Process all files in directory
    results = processor.process_directory()
    
    # Check database
    print("\n" + "=" * 60)
    print("DATABASE CHECK")
    print("=" * 60)
    print(f"Total documents: {Document.objects.count()}")
    print(f"Completed: {Document.objects.filter(status='completed').count()}")
    print(f"Failed: {Document.objects.filter(status='failed').count()}")
    print(f"Total invoices: {Invoice.objects.count()}")
    
    # List all invoices
    print("\nAll invoices in database:")
    for invoice in Invoice.objects.all():
        print(f"  - {invoice.invoice_number}: €{invoice.total_amount} "
              f"({invoice.supplier.name} → {invoice.customer.name})")

if __name__ == "__main__":
    run_batch_test()