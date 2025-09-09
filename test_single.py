import asyncio
from temporalio.client import Client
from temporal_app.workflows import FileProcessingWorkflow
from datetime import datetime

async def test_single_file():
    # Connect to Temporal
    client = await Client.connect("localhost:7233")
    
    # Start workflow - CHANGE THESE VALUES
    handle = await client.start_workflow(
        FileProcessingWorkflow.run,
        args=[
            "test.pdf",  # Your PDF file in Supabase
            "linkledger",  # Your bucket name
            "https://hybiyhovayyyjwkidsof.supabase.co",  # Your Supabase URL
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh5Yml5aG92YXl5eWp3a2lkc29mIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzE4NTMxNSwiZXhwIjoyMDY4NzYxMzE1fQ.UVaPvdrcD4ERqChIRNfvx0J5ZoqYBWNsuYsBXZ06NZ0"  # Your service key
        ],
        id=f"test-single-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        task_queue="file-processing-task-queue",
    )
    
    print(f"Started workflow: {handle.id}")
    result = await handle.result()
    print(f"Result: {result}")

asyncio.run(test_single_file())