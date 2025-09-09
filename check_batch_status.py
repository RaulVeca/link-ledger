import os
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'link_ledger.settings')
django.setup()

from django.db.models import Sum, Count
from file_handler.models import Document, Invoice, ProcessingJob

print("\n" + "="*60)
print("BATCH PROCESSING STATUS REPORT")
print("="*60)
print(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Document statistics
docs = Document.objects.aggregate(
    total=Count('id'),
    completed=Count('id', filter=models.Q(status='completed')),
    failed=Count('id', filter=models.Q(status='failed')),
    pending=Count('id', filter=models.Q(status='pending'))
)

print("\nDocument Processing Status:")
print(f"  Total documents: {docs['total']}")
print(f"  ✓ Completed: {docs['completed']}")
print(f"  ✗ Failed: {docs['failed']}")
print(f"  ⏳ Pending: {docs['pending']}")

# Recent processing
recent = Document.objects.filter(
    processing_completed__gte=datetime.now() - timedelta(hours=24)
).count()
print(f"\nProcessed in last 24 hours: {recent}")

# Invoice statistics
invoice_stats = Invoice.objects.aggregate(
    total_count=Count('id'),
    total_amount=Sum('total_amount')
)

print(f"\nInvoice Statistics:")
print(f"  Total invoices: {invoice_stats['total_count']}")
print(f"  Total amount: €{invoice_stats['total_amount'] or 0:.2f}")

# Failed documents details
failed_docs = Document.objects.filter(status='failed')
if failed_docs:
    print("\nFailed Documents:")
    for doc in failed_docs[:5]:  # Show first 5
        print(f"  - {doc.filename}")
        print(f"    Error: {doc.error_message[:100]}")

# Recent successful invoices
recent_invoices = Invoice.objects.order_by('-created_at')[:5]
if recent_invoices:
    print("\nRecent Invoices:")
    for inv in recent_invoices:
        print(f"  - {inv.invoice_number}: €{inv.total_amount} ({inv.supplier.name})")