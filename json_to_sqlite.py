import json
import sqlite3
from pathlib import Path
from datetime import datetime

class JSONToSQLiteExporter:
    """Export processed invoice data to a standalone SQLite database"""
    
    def __init__(self, output_db='exported_invoices.db'):
        self.output_db = output_db
        self.conn = sqlite3.connect(output_db)
        self.cursor = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        """Create simplified tables for export"""
        
        # Companies table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                vat_number TEXT UNIQUE,
                is_supplier BOOLEAN,
                is_customer BOOLEAN
            )
        ''')
        
        # Invoices table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL,
                invoice_date DATE,
                supplier_id INTEGER,
                customer_id INTEGER,
                total_amount DECIMAL(10,2),
                currency TEXT,
                original_file TEXT,
                FOREIGN KEY (supplier_id) REFERENCES companies(id),
                FOREIGN KEY (customer_id) REFERENCES companies(id)
            )
        ''')
        
        # Invoice items table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER,
                description TEXT,
                quantity DECIMAL(10,4),
                unit_price DECIMAL(10,4),
                total DECIMAL(10,2),
                FOREIGN KEY (invoice_id) REFERENCES invoices(id)
            )
        ''')
        
        self.conn.commit()
    
    def process_json_file(self, json_path):
        """Process a single JSON file and insert into SQLite"""
        
        with open(json_path, 'r', encoding='utf-8') as f:
            ocr_data = json.load(f)
        
        # Extract invoice data using your existing extractor
        from file_handler.services.invoice_extractor import InvoiceExtractor
        extractor = InvoiceExtractor(ocr_data)
        
        # Get or create supplier
        supplier_info = extractor.find_company_info('supplier')
        supplier_id = self._get_or_create_company(
            supplier_info.get('name', 'Unknown'),
            supplier_info.get('vat_number'),
            is_supplier=True
        )
        
        # Get or create customer
        customer_info = extractor.find_company_info('customer')
        customer_id = self._get_or_create_company(
            customer_info.get('name', 'Unknown'),
            customer_info.get('vat_number'),
            is_customer=True
        )
        
        # Insert invoice
        invoice_number = extractor.find_invoice_number()
        amounts = extractor.find_amounts()
        
        self.cursor.execute('''
            INSERT INTO invoices 
            (invoice_number, invoice_date, supplier_id, customer_id, total_amount, currency, original_file)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            invoice_number,
            extractor.find_date('invoice'),
            supplier_id,
            customer_id,
            float(amounts.get('total', 0)),
            'EUR',
            json_path
        ))
        
        self.conn.commit()
        return invoice_number
    
    def _get_or_create_company(self, name, vat_number, is_supplier=False, is_customer=False):
        """Get existing company or create new one"""
        
        if vat_number:
            self.cursor.execute('SELECT id FROM companies WHERE vat_number = ?', (vat_number,))
            result = self.cursor.fetchone()
            if result:
                return result[0]
        
        self.cursor.execute('''
            INSERT INTO companies (name, vat_number, is_supplier, is_customer)
            VALUES (?, ?, ?, ?)
        ''', (name, vat_number, is_supplier, is_customer))
        
        return self.cursor.lastrowid
    
    def export_batch(self, json_dir):
        """Export all JSON files in a directory"""
        json_files = Path(json_dir).glob('*.json')
        count = 0
        
        for json_file in json_files:
            try:
                invoice_num = self.process_json_file(str(json_file))
                print(f"✓ Exported: {invoice_num}")
                count += 1
            except Exception as e:
                print(f"✗ Failed {json_file.name}: {e}")
        
        print(f"\nExported {count} invoices to {self.output_db}")
        return count
    
    def close(self):
        self.conn.close()