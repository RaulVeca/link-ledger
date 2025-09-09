import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'link_ledger.settings')
django.setup()

from supabase import create_client, Client
from file_handler.services.invoice_extractor import InvoiceExtractor
from file_handler.models import Document

def process_directly_from_supabase():
    """Process OCR files directly from Supabase without saving locally"""
    
    # Your credentials
    SUPABASE_URL = "https://hybiyhovayyyjwkidsof.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh5Yml5aG92YXl5eWp3a2lkc29mIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMxODUzMTUsImV4cCI6MjA2ODc2MTMxNX0.z4KnWbnwI0AQ6_lh8J6WAHQh2bRjM4ue0qER0vbKnWY"
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    bucket_name = 'linkledger'
    
    # List files with debugging
    print(f"Checking bucket: {bucket_name}")
    try:
        files = supabase.storage.from_(bucket_name).list()
        print(f"Total files in bucket: {len(files)}")
        
        # Show all files
        if files:
            print("\nAll files in bucket:")
            for file_info in files:
                file_name = file_info['name']
                file_size = file_info.get('metadata', {}).get('size', 0)
                print(f"  - {file_name} ({file_size} bytes)")
        
        # Filter for JSON files
        json_files = [f for f in files if f['name'].endswith('.json')]
        print(f"\nJSON files found: {len(json_files)}")
        
        if json_files:
            for f in json_files:
                print(f"  - {f['name']}")
        else:
            print("\nNo JSON files found in bucket.")
            print("The OCR results might be:")
            print("  1. In a different bucket")
            print("  2. Stored with different extensions")
            print("  3. Not yet uploaded")
                
    except Exception as e:
        print(f"Error accessing bucket '{bucket_name}': {e}")
        print("\nTrying to find available buckets...")
        
        # Try common bucket names
        possible_buckets = ['invoices', 'ocr-results', 'documents', 'uploads']
        for bucket in possible_buckets:
            try:
                test_files = supabase.storage.from_(bucket).list()
                print(f"✓ Found bucket '{bucket}' with {len(test_files)} files")
            except:
                pass

if __name__ == "__main__":
    process_directly_from_supabase()