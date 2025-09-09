import os
import django
import json
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'link_ledger.settings')
django.setup()

from django.conf import settings
from supabase import create_client
from file_handler.services.batch_processor import BatchInvoiceProcessor

def process_supabase_ocr_files():
    """Download and process OCR files from Supabase"""
    
    # Initialize Supabase client
    supabase = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY
    )
    
    # Configuration
    bucket_name = 'invoices'  # Your bucket name where OCR JSONs are stored
    download_dir = Path('supabase_downloads')
    download_dir.mkdir(exist_ok=True)
    
    try:
        # List all files in the bucket
        print(f"Connecting to Supabase bucket: {bucket_name}")
        files = supabase.storage.from_(bucket_name).list()
        
        # Filter for JSON files (OCR results)
        json_files = [f for f in files if f['name'].endswith('.json')]
        print(f"Found {len(json_files)} JSON files in Supabase")
        
        if not json_files:
            print("No JSON files found in bucket")
            return
        
        # Download each file
        local_files = []
        for file_info in json_files:
            file_name = file_info['name']
            print(f"\nDownloading: {file_name}")
            
            try:
                # Download file data
                response = supabase.storage.from_(bucket_name).download(file_name)
                
                # Save locally
                local_path = download_dir / file_name
                
                # Check if it's JSON data
                if isinstance(response, bytes):
                    # Try to parse as JSON to verify it's valid
                    try:
                        json_data = json.loads(response.decode('utf-8'))
                        with open(local_path, 'w', encoding='utf-8') as f:
                            json.dump(json_data, f, indent=2)
                        print(f"  ✓ Saved to: {local_path}")
                        local_files.append(str(local_path))
                    except json.JSONDecodeError:
                        print(f"  ✗ Not valid JSON, skipping")
                        continue
                
            except Exception as e:
                print(f"  ✗ Error downloading {file_name}: {e}")
                continue
        
        if not local_files:
            print("\nNo valid files to process")
            return
        
        # Process all downloaded files
        print("\n" + "="*60)
        print("PROCESSING DOWNLOADED FILES")
        print("="*60)
        
        processor = BatchInvoiceProcessor()
        results = processor.process_file_list(local_files)
        
        return results
        
    except Exception as e:
        print(f"Error accessing Supabase: {e}")
        print("Check your SUPABASE_URL and SUPABASE_KEY in settings.py")
        return None

if __name__ == "__main__":
    process_supabase_ocr_files()