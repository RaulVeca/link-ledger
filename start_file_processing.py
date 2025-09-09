#!/usr/bin/env python
import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from temporalio.client import Client
from temporal_app.workflows import FileProcessingWorkflow


async def main():
    """Start a file processing workflow"""
    
    # Configuration - CHANGE THESE TO YOUR ACTUAL VALUES
    FILENAME = "test.pdf"  # Change to your actual PDF file name in Supabase
    BUCKET_NAME = "linkledger"  # Change to your actual bucket name
    SUPABASE_URL = "https://hybiyhovayyyjwkidsof.supabase.co"  # Change to your Supabase URL
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh5Yml5aG92YXl5eWp3a2lkc29mIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzE4NTMxNSwiZXhwIjoyMDY4NzYxMzE1fQ.UVaPvdrcD4ERqChIRNfvx0J5ZoqYBWNsuYsBXZ06NZ0"  # Change to your Supabase service key
    
    print("=" * 60)
    print("FILE PROCESSING WORKFLOW STARTER")
    print("=" * 60)
    print(f"File: {FILENAME}")
    print(f"Bucket: {BUCKET_NAME}")
    print(f"Supabase URL: {SUPABASE_URL}")
    print("=" * 60)
    
    # Connect to Temporal
    print("Connecting to Temporal server...")
    try:
        client = await Client.connect("localhost:7233")
        print("[SUCCESS] Connected to Temporal server")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Temporal: {e}")
        return
    
    # Generate a unique workflow ID
    workflow_id = f"file-processing-{FILENAME.replace('.', '-')}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Start the workflow
    print(f"\nStarting FileProcessingWorkflow...")
    print(f"Workflow ID: {workflow_id}")
    
    try:
        handle = await client.start_workflow(
            FileProcessingWorkflow.run,
            args=[FILENAME, BUCKET_NAME, SUPABASE_URL, SUPABASE_KEY],  # Pass args as a list
            id=workflow_id,
            task_queue="file-processing-task-queue",
        )
        
        print(f"[SUCCESS] Workflow started with ID: {handle.id}")
        print("\nWaiting for workflow to complete...")
        print("(This may take a few minutes depending on file size)")
        
        # Wait for result
        result = await handle.result()
        
        print("\n" + "=" * 60)
        print("WORKFLOW COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"Result: {result}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] Workflow failed: {e}")
        import traceback
        traceback.print_exc()


async def list_workflows():
    """List recent workflows"""
    print("\nFetching recent workflows...")
    
    client = await Client.connect("localhost:7233")
    
    # List workflows (this is a simplified example)
    print("Recent workflows in the system:")
    # Note: You'd need to use the list_workflows API here
    # This is just a placeholder
    print("Check Temporal Web UI at http://localhost:8088 for workflow history")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Start file processing workflow")
    parser.add_argument("--list", action="store_true", help="List recent workflows")
    parser.add_argument("--file", type=str, help="PDF filename to process")
    parser.add_argument("--bucket", type=str, help="Supabase bucket name")
    parser.add_argument("--url", type=str, help="Supabase URL")
    parser.add_argument("--key", type=str, help="Supabase service key")
    
    args = parser.parse_args()
    
    if args.list:
        asyncio.run(list_workflows())
    else:
        # Override defaults with command line arguments if provided
        if args.file or args.bucket or args.url or args.key:
            print("Note: Update the script with your values or use all arguments")
            print("Usage: python start_file_processing.py --file test.pdf --bucket my-bucket --url https://... --key ...")
        
        asyncio.run(main())