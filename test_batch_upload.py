#!/usr/bin/env python
"""
Test script for batch upload functionality.
Save this as test_batch_upload.py in your project root.
"""

import requests
import json
import sys
import time
from datetime import datetime

# Configuration
DJANGO_SERVER = "http://localhost:8000"  # Adjust if your Django runs on different port
BATCH_UPLOAD_URL = f"{DJANGO_SERVER}/file_handler/batch/upload/"
BATCH_STATUS_URL = f"{DJANGO_SERVER}/file_handler/batch/status/"

def test_batch_upload():
    """Test the batch upload endpoint with sample files"""
    
    # Sample batch upload payload
    # MODIFY THESE WITH YOUR ACTUAL FILES IN SUPABASE
    payload = {
        "files": [
            {"path": "documents/report1.pdf", "bucket": "linkledger"},
            {"path": "documents/report2.pdf", "bucket": "linkledger"},
            {"path": "documents/report3.pdf", "bucket": "linkledger"},
            {"path": "documents/invoice1.pdf", "bucket": "linkledger"},
            {"path": "documents/invoice2.pdf", "bucket": "linkledger"},
        ],
        "priority": "normal",
        "batch_name": "Test Batch - " + datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    print("="*60)
    print("BATCH UPLOAD TEST")
    print("="*60)
    print(f"Endpoint: {BATCH_UPLOAD_URL}")
    print(f"Files to upload: {len(payload['files'])}")
    print(f"Batch name: {payload['batch_name']}")
    print("-"*60)
    
    try:
        # Send the batch upload request
        response = requests.post(
            BATCH_UPLOAD_URL,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            
            print("SUCCESS! Batch uploaded")
            print("-"*60)
            print(f"Batch ID: {result.get('batch_id')}")
            print(f"Total files: {result.get('total_files')}")
            print(f"Successfully queued: {result.get('queued')}")
            print(f"Failed: {result.get('failed')}")
            print(f"Status: {result.get('status')}")
            print(f"\nTemporal UI: {result.get('temporal_ui')}")
            
            # Show queued workflows
            if result.get('workflows'):
                print("\nQueued Workflows:")
                for wf in result['workflows']:
                    print(f"  - {wf['file']}")
                    print(f"    Workflow ID: {wf['workflow_id']}")
                    print(f"    Position: {wf['position']}")
            
            # Show failed files
            if result.get('failures'):
                print("\nFailed Files:")
                for fail in result['failures']:
                    print(f"  - {fail['file']}: {fail['error']}")
            
            return result.get('batch_id')
            
        else:
            print(f"ERROR: Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to Django server")
        print(f"Make sure Django is running on {DJANGO_SERVER}")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def check_batch_status(batch_id):
    """Check the status of a batch"""
    if not batch_id:
        print("No batch ID provided")
        return
    
    url = f"{BATCH_STATUS_URL}{batch_id}/"
    
    print("\n" + "="*60)
    print("CHECKING BATCH STATUS")
    print("="*60)
    print(f"Batch ID: {batch_id}")
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Status: {result.get('status')}")
            print(f"Message: {result.get('message')}")
        else:
            print(f"ERROR: Status check failed with {response.status_code}")
            
    except Exception as e:
        print(f"ERROR: {e}")


def test_high_priority_batch():
    """Test with high priority files"""
    
    payload = {
        "files": [
            {"path": "urgent/critical_doc.pdf", "bucket": "linkledger"},
            {"path": "urgent/priority_report.pdf", "bucket": "linkledger"},
        ],
        "priority": "high",
        "batch_name": "Urgent Processing"
    }
    
    print("\n" + "="*60)
    print("HIGH PRIORITY BATCH TEST")
    print("="*60)
    
    response = requests.post(
        BATCH_UPLOAD_URL,
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"Batch ID: {result.get('batch_id')}")
        print("High priority batch queued successfully!")
        print("These will be processed by the high-priority worker queue")
    else:
        print(f"ERROR: {response.status_code}")


def monitor_batch(batch_id, check_interval=5, max_checks=20):
    """Monitor a batch until completion"""
    
    print(f"\nMonitoring batch {batch_id}...")
    print(f"Checking every {check_interval} seconds...")
    
    for i in range(max_checks):
        # In a real implementation, you'd query Temporal for actual status
        print(f"  Check {i+1}/{max_checks}... (would query Temporal here)")
        time.sleep(check_interval)
        
        # Simulate checking - in reality you'd implement actual Temporal queries
        # check_batch_status(batch_id)
    
    print("\nMonitoring complete. Check Temporal UI for actual status.")


if __name__ == "__main__":
    print("\nBATCH UPLOAD TEST UTILITY")
    print("Make sure:")
    print("  1. Django server is running (python manage.py runserver)")
    print("  2. Temporal server is running (docker-compose up)")
    print("  3. Worker is running (python temporal_app/run_worker.py)")
    print("  4. You have PDF files in your Supabase bucket")
    
    input("\nPress Enter to continue...")
    
    # Test basic batch upload
    batch_id = test_batch_upload()
    
    if batch_id:
        # Check status
        check_batch_status(batch_id)
        
        # Optional: test high priority
        # test_high_priority_batch()
        
        # Optional: monitor the batch
        # monitor_batch(batch_id)
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("Check Temporal UI at http://localhost:8080 to see workflows")
    print("="*60)