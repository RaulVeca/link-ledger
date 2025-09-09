import os
import django
import json
from datetime import date
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'link_ledger.settings')
django.setup()

from file_handler.models import (
    Country, Currency, Company, CompanyAddress,
    Document, Invoice, InvoiceItem
)

def test_basic_setup():
    """Test 1: Create basic reference data"""
    print("=" * 50)
    print("TEST 1: Creating/Getting reference data")
    print("=" * 50)
    
    # Use get_or_create to avoid duplicates
    romania, created = Country.objects.get_or_create(code='RO', defaults={'name': 'Romania'})
    print(f"✓ {'Created' if created else 'Found existing'} country: {romania}")
    
    italy, created = Country.objects.get_or_create(code='IT', defaults={'name': 'Italy'})
    print(f"✓ {'Created' if created else 'Found existing'} country: {italy}")
    
    eur, created = Currency.objects.get_or_create(code='EUR', defaults={'name': 'Euro', 'symbol': '€'})
    print(f"✓ {'Created' if created else 'Found existing'} currency: {eur}")
    
    return romania, italy, eur

def test_company_creation():
    """Test 2: Create companies"""
    print("\n" + "=" * 50)
    print("TEST 2: Creating/Getting companies")
    print("=" * 50)
    
    # Use get_or_create for companies too
    sensidev, created = Company.objects.get_or_create(
        vat_number='RO30428638',
        defaults={
            'name': 'SC SENSIDEV SRL',
            'is_customer': True
        }
    )
    print(f"✓ {'Created' if created else 'Found existing'} customer: {sensidev}")
    
    amazon, created = Company.objects.get_or_create(
        vat_number='IT08973230967',
        defaults={
            'name': 'Amazon EU S.à r.l.',
            'is_supplier': True
        }
    )
    print(f"✓ {'Created' if created else 'Found existing'} supplier: {amazon}")
    
    return sensidev, amazon

def test_invoice_creation(customer, supplier, currency):
    """Test 3: Create an invoice with items"""
    print("\n" + "=" * 50)
    print("TEST 3: Creating invoice with items")
    print("=" * 50)
    
    # Check if invoice already exists
    invoice_number = 'AEU-INV-IT-2020-1016055'
    
    existing_invoice = Invoice.objects.filter(
        invoice_number=invoice_number,
        supplier=supplier
    ).first()
    
    if existing_invoice:
        print(f"✓ Found existing invoice: {existing_invoice}")
        return existing_invoice
    
    # Create a document record
    doc = Document.objects.create(
        filename='amazon_invoice.pdf',
        bucket_name='invoices',
        file_path='/invoices/2020/amazon_invoice.pdf',
        status='completed'
    )
    print(f"✓ Created document: {doc}")
    
    # Create invoice
    invoice = Invoice.objects.create(
        document=doc,
        invoice_number=invoice_number,
        invoice_date=date(2020, 11, 9),
        supplier=supplier,
        customer=customer,
        currency=currency,
        subtotal=Decimal('99.14'),
        tax_amount=Decimal('0.00'),
        total_amount=Decimal('107.16')
    )
    print(f"✓ Created invoice: {invoice}")
    
    # Create invoice item
    item = InvoiceItem.objects.create(
        invoice=invoice,
        line_number=1,
        description='beyerdynamic DT 990 PRO Over-Ear-Studiokopfhörer',
        quantity=Decimal('1'),
        unit_price=Decimal('99.14'),
        tax_rate=Decimal('0'),
        subtotal=Decimal('99.14'),
        total=Decimal('99.14')
    )
    print(f"✓ Created invoice item: {item.description[:50]}...")
    
    # Add shipping as second item
    shipping = InvoiceItem.objects.create(
        invoice=invoice,
        line_number=2,
        description='Versandkosten',
        quantity=Decimal('1'),
        unit_price=Decimal('8.02'),
        tax_rate=Decimal('0'),
        subtotal=Decimal('8.02'),
        total=Decimal('8.02')
    )
    print(f"✓ Created shipping item: {shipping.description}")
    
    return invoice

def test_ocr_data_processing():
    """Test 4: Process your actual OCR JSON"""
    print("\n" + "=" * 50)
    print("TEST 4: Processing OCR data")
    print("=" * 50)
    
    # Load your OCR JSON
    try:
        with open('invoice_ocr.json', 'r') as f:
            ocr_data = json.load(f)
        print(f"✓ Loaded OCR data: {ocr_data['metadata']['original_filename']}")
        
        # Extract some text
        first_page = ocr_data['pages'][0]
        text_blocks = []
        for block in first_page['blocks']:
            for line in block['lines']:
                text = ' '.join([word['value'] for word in line['words']])
                text_blocks.append(text)
        
        print(f"✓ Extracted {len(text_blocks)} text blocks")
        
        # Find invoice number in OCR
        invoice_num = None
        for text in text_blocks:
            if 'AEU-INV' in text:
                invoice_num = text
                break
        
        if invoice_num:
            print(f"✓ Found invoice number in OCR: {invoice_num}")
        
        # Find amounts
        for text in text_blocks:
            if '107,16' in text or '107.16' in text:
                print(f"✓ Found total amount in OCR: {text}")
                break
            
    except FileNotFoundError:
        print("✗ invoice_ocr.json not found - skipping OCR test")
    except Exception as e:
        print(f"✗ Error processing OCR: {e}")

def test_queries():
    """Test 5: Query the data"""
    print("\n" + "=" * 50)
    print("TEST 5: Querying data")
    print("=" * 50)
    
    # Count records
    print(f"✓ Total countries: {Country.objects.count()}")
    print(f"✓ Total companies: {Company.objects.count()}")
    print(f"✓ Total invoices: {Invoice.objects.count()}")
    print(f"✓ Total documents: {Document.objects.count()}")
    
    # Find invoices for Sensidev
    sensidev_invoices = Invoice.objects.filter(customer__name__contains='SENSIDEV')
    print(f"✓ Invoices for Sensidev: {sensidev_invoices.count()}")
    
    # List all invoices
    for inv in Invoice.objects.all():
        print(f"  - {inv.invoice_number}: {inv.supplier.name} → {inv.customer.name} = €{inv.total_amount}")
    
    # Calculate total spending
    from django.db.models import Sum
    total = Invoice.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    print(f"✓ Total invoice amount: €{total}")

def cleanup():
    """Optional: Clean up test data"""
    print("\n" + "=" * 50)
    print("CLEANUP OPTIONS")
    print("=" * 50)
    
    print("What would you like to do?")
    print("1. Keep all data")
    print("2. Delete only test invoices")
    print("3. Delete everything (full reset)")
    
    response = input("Choose (1/2/3): ")
    
    if response == '2':
        Invoice.objects.all().delete()
        Document.objects.all().delete()
        print("✓ Deleted invoices and documents")
    elif response == '3':
        # Delete in correct order to respect foreign keys
        InvoiceItem.objects.all().delete()
        Invoice.objects.all().delete()
        Document.objects.all().delete()
        Company.objects.all().delete()
        Currency.objects.all().delete()
        Country.objects.all().delete()
        print("✓ All data deleted - database reset")
    else:
        print("✓ Data kept")

if __name__ == "__main__":
    try:
        print("\n🚀 STARTING DATABASE TESTS\n")
        
        # Run tests
        romania, italy, eur = test_basic_setup()
        sensidev, amazon = test_company_creation()
        invoice = test_invoice_creation(sensidev, amazon, eur)
        test_ocr_data_processing()
        test_queries()
        
        print("\n✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        
        # Optional cleanup
        cleanup()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()