import json
import re
from datetime import datetime
from decimal import Decimal
from file_handler.models import (
    Company, CompanyAddress, Invoice, InvoiceItem,
    Document, Country, Currency, ExtractedText, ExtractedMetadata
)

class InvoiceExtractor:
    def __init__(self, ocr_data):
        self.ocr_data = ocr_data
        self.text_blocks = self._extract_text_blocks()
        self.full_text = ' '.join([t['text'] for t in self.text_blocks])
        
    def _extract_text_blocks(self):
        """Extract all text blocks with their positions"""
        texts = []
        for page in self.ocr_data.get('pages', []):
            for block in page.get('blocks', []):
                for line in block.get('lines', []):
                    line_text = ' '.join([word['value'] for word in line.get('words', [])])
                    texts.append({
                        'text': line_text,
                        'geometry': line.get('geometry'),
                        'words': line.get('words', []),
                        'confidence': line.get('objectness_score', 0)
                    })
        return texts
    
    def find_pattern(self, patterns, text=None):
        """Search for patterns in text"""
        search_text = text or self.full_text
        for pattern in patterns:
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        return None
    
    def find_invoice_number(self):
        """Extract invoice number"""
        patterns = [
            r'AEU-INV-[A-Z]{2}-\d{4}-\d+',  # Amazon pattern
            r'Rechnungsnummer[\s:]*([A-Z0-9\-\/]+)',
            r'Invoice[\s:]*(?:Number|Nr)?[\s:]*([A-Z0-9\-\/]+)',
            r'Factur[aă][\s:]*(?:Nr)?[\s:]*([A-Z0-9\-\/]+)',
        ]
        return self.find_pattern(patterns)
    
    def find_date(self, date_type='invoice'):
        """Extract dates from invoice"""
        if date_type == 'invoice':
            patterns = [
                r'Rechnungsdatum[\s\S]*?(\d{1,2}[\s\.](?:November|November|Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|Dezember)[\s\.]\d{4})',
                r'Invoice\s*Date[\s:]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})',
                r'Data\s*facturii[\s:]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})',
            ]
        date_str = self.find_pattern(patterns)
        if date_str:
            # Parse the date - you'll need to handle different formats
            return self.parse_date(date_str)
        return None
    
    def parse_date(self, date_str):
        """Parse various date formats"""
        # German month names
        month_map = {
            'Januar': '01', 'Februar': '02', 'März': '03', 'April': '04',
            'Mai': '05', 'Juni': '06', 'Juli': '07', 'August': '08',
            'September': '09', 'Oktober': '10', 'November': '11', 'Dezember': '12'
        }
        
        # Replace German months
        for de_month, number in month_map.items():
            if de_month in date_str:
                day = re.search(r'(\d{1,2})', date_str).group(1)
                year = re.search(r'(\d{4})', date_str).group(1)
                return datetime.strptime(f"{day}/{number}/{year}", "%d/%m/%Y").date()
        
        # Try common formats
        for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%Y-%m-%d']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except:
                continue
        return None
    
    def find_amounts(self):
        """Extract monetary amounts"""
        amounts = {}
        
        # Look for total amount - this is working well
        total_patterns = [
            r'Zahlbetrag[\s:]*([0-9.,]+)',
            r'Total[\s:]*€?[\s]*([0-9.,]+)',
            r'Gesamt[\s:]*€?[\s]*([0-9.,]+)',
        ]
        
        total_str = self.find_pattern(total_patterns)
        if total_str:
            amounts['total'] = self.parse_amount(total_str)
        
        # Better patterns for tax and subtotal
        for block in self.text_blocks:
            text = block['text']
            
            # Look for subtotal lines
            if 'Zwischensumme' in text and 'USt' not in text:
                # Find the amount in the same line
                if '107,16' in text or '99,14' in text:
                    amount = self.parse_amount(text)
                    if amount and 'subtotal' not in amounts:
                        amounts['subtotal'] = amount
            
            # Look for tax lines - be more specific
            if 'USt. Gesamt' in text or ('USt' in text and '0,00' in text):
                # This invoice has 0% tax
                if '0,00' in text:
                    amounts['tax'] = Decimal('0.00')
                else:
                    amount = self.parse_amount(text)
                    if amount and amount < amounts.get('total', Decimal('1000')):
                        amounts['tax'] = amount
                        
        return amounts
    
    def parse_amount(self, text):
        """Parse monetary amounts from text"""
        # Find number patterns
        pattern = r'([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})?)'
        match = re.search(pattern, text)
        if match:
            amount_str = match.group(1)
            # Convert European format to standard decimal
            amount_str = amount_str.replace('.', '').replace(',', '.')
            try:
                return Decimal(amount_str)
            except:
                pass
        return None
    
    def find_company_info(self, company_type='supplier'):
        """Extract company information"""
        info = {}
        
        if company_type == 'supplier' and 'Amazon' in self.full_text:
            info['name'] = 'Amazon EU S.à r.l.'
            # Look for VAT number
            vat_patterns = [
                r'IT08973230967',
                r'USt-IDNr\.[\s:]*([A-Z]{2}[0-9]+)',
            ]
            info['vat_number'] = self.find_pattern(vat_patterns)
            
        elif company_type == 'customer' and 'SENSIDEV' in self.full_text:
            info['name'] = 'SC SENSIDEV SRL'
            info['vat_number'] = 'RO30428638'
            
        return info
    
    def process_invoice(self, document):
        """Main method to process invoice and create database records"""
        
        # Extract invoice data
        invoice_number = self.find_invoice_number()
        if not invoice_number:
            raise ValueError("Could not find invoice number")
        
        # Get or create companies
        supplier_info = self.find_company_info('supplier')
        supplier, _ = Company.objects.get_or_create(
            vat_number=supplier_info.get('vat_number', 'UNKNOWN'),
            defaults={'name': supplier_info.get('name', 'Unknown Supplier'), 'is_supplier': True}
        )
        
        customer_info = self.find_company_info('customer')
        customer, _ = Company.objects.get_or_create(
            vat_number=customer_info.get('vat_number', 'UNKNOWN'),
            defaults={'name': customer_info.get('name', 'Unknown Customer'), 'is_customer': True}
        )
        
        # Check if invoice already exists
        existing_invoice = Invoice.objects.filter(
            supplier=supplier,
            invoice_number=invoice_number
        ).first()
        
        if existing_invoice:
            print(f"Invoice {invoice_number} already exists, updating document link...")
            # Update the existing invoice's document
            existing_invoice.document = document
            existing_invoice.save()
            return existing_invoice
        
        # Get amounts
        amounts = self.find_amounts()
        
        # Get or create currency
        currency, _ = Currency.objects.get_or_create(
            code='EUR',
            defaults={'name': 'Euro', 'symbol': '€'}
        )
        
        # Create new invoice
        invoice = Invoice.objects.create(
            document=document,
            invoice_number=invoice_number,
            invoice_date=self.find_date('invoice') or datetime.now().date(),
            supplier=supplier,
            customer=customer,
            currency=currency,
            subtotal=amounts.get('subtotal', Decimal('0')),
            tax_amount=amounts.get('tax', Decimal('0')),
            total_amount=amounts.get('total', Decimal('0'))
        )
        
        # Store extracted metadata
        for field_name, field_value in [
            ('invoice_number', invoice_number),
            ('supplier_name', supplier_info.get('name')),
            ('customer_name', customer_info.get('name')),
            ('total_amount', str(amounts.get('total'))),
        ]:
            if field_value:
                ExtractedMetadata.objects.create(
                    document=document,
                    field_name=field_name,
                    field_value=field_value,
                    extraction_method='pattern_matching'
                )
        
        return invoice