from django.contrib import admin
from .models import Company, Invoice, InvoiceItem, Document

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'vat_number', 'is_supplier', 'is_customer']
    search_fields = ['name', 'vat_number']

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'supplier', 'customer', 'invoice_date', 'total_amount']
    list_filter = ['invoice_date', 'supplier']
    date_hierarchy = 'invoice_date'

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'status', 'upload_date']
    list_filter = ['status']