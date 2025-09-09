# models.py - Django Models for Normalized Invoice Database

from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid

# ============= COMPANY ENTITIES =============

class Country(models.Model):
    """Normalized country table"""
    code = models.CharField(max_length=2, primary_key=True)  # ISO 3166-1 alpha-2
    name = models.CharField(max_length=100)
    
    class Meta:
        db_table = 'countries'
        verbose_name_plural = 'Countries'
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class Currency(models.Model):
    """Normalized currency table"""
    code = models.CharField(max_length=3, primary_key=True)  # ISO 4217
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=5, blank=True)
    
    class Meta:
        db_table = 'currencies'
        verbose_name_plural = 'Currencies'
    
    def __str__(self):
        return self.code


class Company(models.Model):
    """Base company information - both suppliers and customers"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    legal_name = models.CharField(max_length=255, blank=True)
    vat_number = models.CharField(max_length=50, blank=True, db_index=True)
    registration_number = models.CharField(max_length=100, blank=True)
    tax_code = models.CharField(max_length=50, blank=True)
    
    # Denormalized for frequent access
    is_supplier = models.BooleanField(default=False)
    is_customer = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'companies'
        verbose_name_plural = 'Companies'
        indexes = [
            models.Index(fields=['vat_number']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return self.name


class CompanyAddress(models.Model):
    """Company addresses - supports multiple addresses per company"""
    ADDRESS_TYPES = [
        ('billing', 'Billing'),
        ('shipping', 'Shipping'),
        ('headquarters', 'Headquarters'),
        ('branch', 'Branch'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPES)
    
    street = models.CharField(max_length=255)
    street_number = models.CharField(max_length=20, blank=True)
    building = models.CharField(max_length=50, blank=True)
    apartment = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100)
    state_province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    
    is_primary = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'company_addresses'
        verbose_name_plural = 'Company Addresses'
        unique_together = [['company', 'address_type', 'is_primary']]
    
    def __str__(self):
        return f"{self.company.name} - {self.get_address_type_display()}"


class CompanyBankAccount(models.Model):
    """Bank account information for companies"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='bank_accounts')
    
    bank_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=50, blank=True)
    iban = models.CharField(max_length=34, blank=True)
    swift_code = models.CharField(max_length=11, blank=True)
    
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'company_bank_accounts'
        verbose_name = 'Company Bank Account'
    
    def __str__(self):
        return f"{self.company.name} - {self.bank_name}"


# ============= DOCUMENT PROCESSING =============

class Document(models.Model):
    """Main document record for tracking files"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('verified', 'Verified'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255)
    bucket_name = models.CharField(max_length=100)
    file_path = models.CharField(max_length=500)
    
    file_size = models.BigIntegerField(null=True, blank=True)
    file_hash = models.CharField(max_length=64, blank=True)  # SHA-256
    
    upload_date = models.DateTimeField(auto_now_add=True)
    processing_started = models.DateTimeField(null=True, blank=True)
    processing_completed = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    
    # Temporal workflow tracking
    workflow_id = models.CharField(max_length=255, blank=True, unique=True, null=True)
    batch_id = models.CharField(max_length=100, blank=True, db_index=True)
    priority = models.CharField(max_length=20, default='normal')
    
    class Meta:
        db_table = 'documents'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['batch_id']),
            models.Index(fields=['upload_date']),
        ]
    
    def __str__(self):
        return self.filename


class ProcessingJob(models.Model):
    """Track document processing attempts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='processing_jobs')
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    success = models.BooleanField(default=False)
    error_details = models.TextField(blank=True)
    
    # OCR specific metrics
    pages_processed = models.IntegerField(default=0)
    confidence_score = models.FloatField(null=True, blank=True)
    processing_time_seconds = models.FloatField(null=True, blank=True)
    
    class Meta:
        db_table = 'processing_jobs'
        indexes = [
            models.Index(fields=['started_at']),
        ]


# ============= INVOICE STRUCTURE =============

class Invoice(models.Model):
    """Main invoice table"""
    INVOICE_TYPES = [
        ('standard', 'Standard Invoice'),
        ('proforma', 'Proforma'),
        ('credit_note', 'Credit Note'),
        ('vat_invoice', 'VAT Invoice'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='invoices')
    
    # Core invoice data
    invoice_number = models.CharField(max_length=100, db_index=True)
    invoice_series = models.CharField(max_length=50, blank=True)
    invoice_type = models.CharField(max_length=20, choices=INVOICE_TYPES, default='standard')
    
    invoice_date = models.DateField(db_index=True)
    due_date = models.DateField(null=True, blank=True)
    
    # Company relationships
    supplier = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='invoices_as_supplier')
    customer = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='invoices_as_customer')
    
    # Financial data
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # Additional info
    order_reference = models.CharField(max_length=100, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    # Period coverage (for service invoices)
    service_period_start = models.DateField(null=True, blank=True)
    service_period_end = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'invoices'
        unique_together = [['supplier', 'invoice_number']]
        indexes = [
            models.Index(fields=['invoice_date']),
            models.Index(fields=['due_date']),
            models.Index(fields=['supplier', 'invoice_date']),
            models.Index(fields=['customer', 'invoice_date']),
        ]
    
    def __str__(self):
        return f"{self.invoice_number} - {self.supplier.name}"


class InvoiceItem(models.Model):
    """Individual line items on invoices"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    
    line_number = models.IntegerField()
    
    # Product/Service info
    product_code = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    
    # Quantities and amounts
    quantity = models.DecimalField(max_digits=15, decimal_places=4, default=Decimal('1.0000'))
    unit_of_measure = models.CharField(max_length=20, blank=True)
    unit_price = models.DecimalField(max_digits=15, decimal_places=4)
    
    # Tax info
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # Totals
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    total = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Service period (if applicable)
    service_period_start = models.DateField(null=True, blank=True)
    service_period_end = models.DateField(null=True, blank=True)
    
    class Meta:
        db_table = 'invoice_items'
        ordering = ['invoice', 'line_number']
        unique_together = [['invoice', 'line_number']]
    
    def save(self, *args, **kwargs):
        # Auto-calculate totals if not set
        if not self.subtotal:
            self.subtotal = self.quantity * self.unit_price
        if not self.total:
            self.total = self.subtotal + self.tax_amount
        super().save(*args, **kwargs)


class TaxDetail(models.Model):
    """Separate tax details for complex tax scenarios"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='tax_details')
    
    tax_type = models.CharField(max_length=50)  # VAT, GST, etc.
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2)
    taxable_amount = models.DecimalField(max_digits=15, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    description = models.CharField(max_length=255, blank=True)
    
    class Meta:
        db_table = 'tax_details'
    
    def __str__(self):
        return f"{self.tax_type} {self.tax_rate}% - {self.invoice.invoice_number}"


class Payment(models.Model):
    """Payment tracking for invoices"""
    PAYMENT_METHODS = [
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('stripe', 'Stripe'),
        ('pos', 'POS Terminal'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    reference_number = models.CharField(max_length=100, blank=True)
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payments'
        indexes = [
            models.Index(fields=['payment_date']),
        ]


# ============= OCR EXTRACTION DATA =============

class ExtractedPage(models.Model):
    """Store OCR page-level data"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='extracted_pages')
    
    page_number = models.IntegerField()
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    
    confidence_score = models.FloatField(null=True, blank=True)
    
    class Meta:
        db_table = 'extracted_pages'
        unique_together = [['document', 'page_number']]
        ordering = ['document', 'page_number']


class ExtractedText(models.Model):
    """Store OCR text blocks with positioning"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.ForeignKey(ExtractedPage, on_delete=models.CASCADE, related_name='text_blocks')
    
    text_content = models.TextField()
    confidence_score = models.FloatField(null=True, blank=True)
    
    # Bounding box coordinates
    bbox_x1 = models.FloatField(null=True, blank=True)
    bbox_y1 = models.FloatField(null=True, blank=True)
    bbox_x2 = models.FloatField(null=True, blank=True)
    bbox_y2 = models.FloatField(null=True, blank=True)
    
    # Text properties
    font_size = models.FloatField(null=True, blank=True)
    is_bold = models.BooleanField(default=False)
    is_italic = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'extracted_text'
        indexes = [
            models.Index(fields=['page']),
        ]


class ExtractedMetadata(models.Model):
    """Key-value pairs extracted from documents"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='metadata')
    
    field_name = models.CharField(max_length=100, db_index=True)
    field_value = models.TextField()
    field_type = models.CharField(max_length=50, blank=True)  # date, amount, text, etc.
    
    confidence_score = models.FloatField(null=True, blank=True)
    page_number = models.IntegerField(null=True, blank=True)
    
    # For tracking which extraction method/model found this
    extraction_method = models.CharField(max_length=50, blank=True)
    
    class Meta:
        db_table = 'extracted_metadata'
        indexes = [
            models.Index(fields=['document', 'field_name']),
        ]


# ============= AUDIT & TRACKING =============

class InvoiceAuditLog(models.Model):
    """Audit trail for invoice changes"""
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('deleted', 'Deleted'),
        ('verified', 'Verified'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='audit_logs')
    
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    user = models.CharField(max_length=100, blank=True)  # Can link to User model
    changes = models.JSONField(blank=True, null=True)  # Store what changed
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'invoice_audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['invoice', 'timestamp']),
        ]