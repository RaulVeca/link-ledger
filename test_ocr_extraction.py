import os
import django
import json
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'link_ledger.settings')
django.setup()

from file_handler.services.invoice_extractor import InvoiceExtractor
from file_handler.models import Document, Invoice

print("=" * 60)
print("OCR EXTRACTION TEST")
print("=" * 60)

# Load your OCR JSON
with open('invoice_ocr.json', 'r') as f:
    ocr_data = json.load(f)
    print(f"✓ Loaded OCR file: {ocr_data['metadata']['original_filename']}")

# Create a document record
document = Document.objects.create(
    filename='amazon_ocr_test.pdf',
    bucket_name='test',
    file_path='test/amazon_ocr_test.pdf',
    status='processing'
)
print(f"✓ Created document record: {document.filename}")

# Process the invoice
extractor = InvoiceExtractor(ocr_data)

print("\n" + "=" * 60)
print("EXTRACTED DATA:")
print("=" * 60)

# Test individual extraction methods
invoice_num = extractor.find_invoice_number()
print(f"Invoice Number: {invoice_num}")

amounts = extractor.find_amounts()
print(f"Amounts Found:")
print(f"  - Total: €{amounts.get('total', 'Not found')}")
print(f"  - Tax: €{amounts.get('tax', 'Not found')}")
print(f"  - Subtotal: €{amounts.get('subtotal', 'Not found')}")

supplier = extractor.find_company_info('supplier')
print(f"Supplier: {supplier.get('name')} (VAT: {supplier.get('vat_number')})")

customer = extractor.find_company_info('customer')
print(f"Customer: {customer.get('name')} (VAT: {customer.get('vat_number')})")

print("\n" + "=" * 60)
print("PROCESSING INVOICE:")
print("=" * 60)

# Process complete invoice
try:
    invoice = extractor.process_invoice(document)
    print(f"✓ Invoice processed successfully!")
    print(f"  Invoice #: {invoice.invoice_number}")
    print(f"  Supplier: {invoice.supplier.name}")
    print(f"  Customer: {invoice.customer.name}")
    print(f"  Date: {invoice.invoice_date}")
    print(f"  Total: €{invoice.total_amount}")
    
    document.status = 'completed'
    document.save()
    
except Exception as e:
    print(f"✗ Error processing invoice: {e}")
    document.status = 'failed'
    document.error_message = str(e)
    document.save()

print("\n" + "=" * 60)
print("DATABASE STATUS:")
print("=" * 60)
print(f"Total invoices in database: {Invoice.objects.count()}")
print(f"Invoices for this supplier: {Invoice.objects.filter(supplier__name__contains='Amazon').count()}")

# List all invoices
print("\nAll invoices:")
for inv in Invoice.objects.all():
    print(f"  - {inv.invoice_number}: €{inv.total_amount} ({inv.supplier.name})")