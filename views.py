import asyncio
import json
import sys
import traceback
import uuid
from datetime import datetime
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from asgiref.sync import async_to_sync, sync_to_async

# Add Temporal client and workflow imports
from temporalio.client import Client as TemporalClient
from temporal_app.workflows import FileProcessingWorkflow

from file_handler.services.invoice_extractor import InvoiceExtractor
from file_handler.models import Document

def process_ocr_result(ocr_json_path, original_filename):
    # Create document record
    document = Document.objects.create(
        filename=original_filename,
        bucket_name='your-bucket',
        file_path=ocr_json_path,
        status='processing'
    )
    # ... rest of the function


# Helper function to handle the async Temporal operations
async def start_temporal_workflow(file_path, bucket_name):
    """
    Connects to Temporal and starts the file processing workflow.
    """
    print(f"   Connecting to Temporal server...")
    temporal_client = await TemporalClient.connect("localhost:7233")
    print(f"   Connected to Temporal successfully")
    
    # Generate a valid workflow ID (replace problematic characters)
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    safe_filename = file_path.replace('/', '-').replace('.', '-').replace(' ', '-')
    workflow_id = f"file-processing-{safe_filename}-{timestamp}"
    
    print(f"   Starting workflow with ID: {workflow_id}")
    
    # The workflow expects 4 arguments passed as a list
    handle = await temporal_client.start_workflow(
        FileProcessingWorkflow.run,
        args=[file_path, bucket_name, settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY],
        id=workflow_id,
        task_queue="file-processing-task-queue",
    )
    
    print(f"   Workflow started successfully!")
    return handle.id


async def start_temporal_workflow_with_metadata(
    file_path, 
    bucket_name, 
    batch_id=None,
    batch_name=None,
    priority='normal',
    position=0
):
    """
    Enhanced version of start_temporal_workflow with batch metadata.
    """
    print(f"   Connecting to Temporal server...")
    temporal_client = await TemporalClient.connect("localhost:7233")
    
    # Generate workflow ID with batch info
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    safe_filename = file_path.replace('/', '-').replace('.', '-').replace(' ', '-')
    
    # Include batch ID in workflow ID if part of a batch
    if batch_id:
        workflow_id = f"batch-{batch_id[:8]}-{position:03d}-{safe_filename}-{timestamp}"
    else:
        workflow_id = f"file-processing-{safe_filename}-{timestamp}"
    
    print(f"   Starting workflow with ID: {workflow_id}")
    
    # The workflow expects 4 arguments passed as a list
    handle = await temporal_client.start_workflow(
        FileProcessingWorkflow.run,
        args=[file_path, bucket_name, settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY],
        id=workflow_id,
        task_queue=get_task_queue_by_priority(priority),
    )
    
    return handle.id


def get_task_queue_by_priority(priority):
    """
    Map priority to different task queues for priority-based processing.
    """
    priority_queues = {
        'high': 'file-processing-high-priority',
        'normal': 'file-processing-task-queue',
        'low': 'file-processing-low-priority'
    }
    return priority_queues.get(priority, 'file-processing-task-queue')


@csrf_exempt
def supabase_webhook(request):
    """
    Webhook endpoint for Supabase storage events.
    Triggers a Temporal workflow to process uploaded files.
    """
    print("\n" + "="*60)
    print("WEBHOOK RECEIVED - PROCESSING FILE UPLOAD")
    print("="*60)
    sys.stdout.flush()
    
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request method.")
    
    try:
        # 1. Parse data from webhook
        data = json.loads(request.body)
        print(f"Webhook payload type: {data.get('type', 'unknown')}")
        
        # Handle different webhook payload structures
        # Supabase can send either 'record' or 'Record' depending on configuration
        record = data.get('record') or data.get('Record', {})
        
        # Sometimes the data is nested differently
        if not record and 'new' in data:
            record = data.get('new', {})
        
        bucket_name = record.get('bucket_id') or record.get('bucket_name')
        file_path = record.get('name') or record.get('path')
        
        print(f"Parsed webhook data:")
        print(f"  Bucket: {bucket_name}")
        print(f"  File: {file_path}")
        print(f"  Record keys: {list(record.keys())}")
        sys.stdout.flush()
        
        # Validate required fields
        if not file_path or not bucket_name:
            print("ERROR: Missing required fields")
            print(f"  file_path: {file_path}")
            print(f"  bucket_name: {bucket_name}")
            print(f"  Full record: {json.dumps(record, indent=2)}")
            return HttpResponseBadRequest("Missing file_path or bucket_name.")
        
        # Skip files that are already processed (in json-output folder)
        if file_path.startswith('json-output/'):
            print(f"Skipping already processed file: {file_path}")
            return HttpResponse(status=204)
        
        # Only process PDF files
        if not file_path.lower().endswith('.pdf'):
            print(f"Skipping non-PDF file: {file_path}")
            return HttpResponse("Skipping non-PDF file", status=200)
        
        print(f"\n1. Processing new PDF file: {file_path}")
        print(f"   Bucket: {bucket_name}")
        sys.stdout.flush()
        
        # 2. Check that we have the required settings
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            print("ERROR: Missing Supabase configuration")
            print(f"  SUPABASE_URL: {'Set' if settings.SUPABASE_URL else 'Missing'}")
            print(f"  SUPABASE_SERVICE_KEY: {'Set' if settings.SUPABASE_SERVICE_KEY else 'Missing'}")
            return HttpResponse("Server configuration error", status=500)
        
        # 3. Start the Temporal workflow
        print("\n2. Starting Temporal workflow...")
        sys.stdout.flush()
        
        try:
            # Use async_to_sync to run the async function in a sync Django view
            workflow_id = async_to_sync(start_temporal_workflow)(file_path, bucket_name)
            
            print(f"\n3. SUCCESS! Workflow ID: {workflow_id}")
            print("   Check Temporal UI at: http://localhost:8080")
            print("   Check worker logs for processing details")
            print("="*60)
            sys.stdout.flush()
            
            return HttpResponse(f"Workflow started: {workflow_id}", status=200)
            
        except Exception as temporal_error:
            print(f"\nERROR starting Temporal workflow: {temporal_error}")
            print("Make sure:")
            print("  1. Temporal server is running (docker-compose up)")
            print("  2. Worker is running (python temporal_app/run_worker.py)")
            traceback.print_exc()
            return HttpResponse(f"Failed to start workflow: {str(temporal_error)}", status=500)
        
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in request body: {e}")
        print(f"Raw body: {request.body[:500]}")  # Print first 500 chars
        return HttpResponseBadRequest("Invalid JSON payload.")
    
    except Exception as e:
        print("\n" + "!"*60)
        print(f"UNEXPECTED ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()
        print("!"*60)
        return HttpResponse(f"Internal server error: {str(e)}", status=500)


@csrf_exempt
@require_http_methods(["POST"])
def batch_upload_files(request):
    """
    Batch upload endpoint that queues multiple files for processing.
    
    Expected JSON payload:
    {
        "files": [
            {"path": "document1.pdf", "bucket": "linkledger"},
            {"path": "document2.pdf", "bucket": "linkledger"},
            ...
        ],
        "priority": "normal",  # optional: "high", "normal", "low"
        "batch_name": "Q4 Reports"  # optional: for grouping
    }
    """
    print("\n" + "="*60)
    print("BATCH UPLOAD REQUEST RECEIVED")
    print("="*60)
    
    try:
        data = json.loads(request.body)
        files = data.get('files', [])
        priority = data.get('priority', 'normal')
        batch_name = data.get('batch_name', f'batch_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        
        if not files:
            return JsonResponse({
                'error': 'No files provided',
                'status': 'failed'
            }, status=400)
        
        # Generate batch ID for tracking
        batch_id = str(uuid.uuid4())
        
        print(f"Processing batch: {batch_name}")
        print(f"Batch ID: {batch_id}")
        print(f"Number of files: {len(files)}")
        print(f"Priority: {priority}")
        
        # Store results for response
        queued_workflows = []
        failed_files = []
        
        # Process each file
        for idx, file_info in enumerate(files):
            file_path = file_info.get('path')
            bucket_name = file_info.get('bucket', 'linkledger')  # default bucket
            
            if not file_path:
                failed_files.append({
                    'file': file_info,
                    'error': 'Missing file path'
                })
                continue
            
            # Skip non-PDF files
            if not file_path.lower().endswith('.pdf'):
                failed_files.append({
                    'file': file_path,
                    'error': 'Not a PDF file'
                })
                continue
            
            # Skip already processed files
            if file_path.startswith('json-output/'):
                failed_files.append({
                    'file': file_path,
                    'error': 'Already processed'
                })
                continue
            
            try:
                # Start Temporal workflow for this file
                workflow_id = async_to_sync(start_temporal_workflow_with_metadata)(
                    file_path, 
                    bucket_name,
                    batch_id,
                    batch_name,
                    priority,
                    idx  # position in batch
                )
                
                queued_workflows.append({
                    'file': file_path,
                    'workflow_id': workflow_id,
                    'status': 'queued',
                    'position': idx + 1
                })
                
                print(f"  [{idx+1}/{len(files)}] Queued: {file_path} -> {workflow_id}")
                
            except Exception as e:
                print(f"  [{idx+1}/{len(files)}] Failed: {file_path} - {str(e)}")
                failed_files.append({
                    'file': file_path,
                    'error': str(e)
                })
        
        # Prepare response
        response_data = {
            'batch_id': batch_id,
            'batch_name': batch_name,
            'total_files': len(files),
            'queued': len(queued_workflows),
            'failed': len(failed_files),
            'workflows': queued_workflows,
            'failures': failed_files,
            'status': 'processing',
            'temporal_ui': 'http://localhost:8080',
            'message': f'Successfully queued {len(queued_workflows)} of {len(files)} files'
        }
        
        print("\n" + "="*60)
        print(f"BATCH UPLOAD COMPLETE")
        print(f"  Queued: {len(queued_workflows)} files")
        print(f"  Failed: {len(failed_files)} files")
        print("="*60)
        
        return JsonResponse(response_data, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON payload',
            'status': 'failed'
        }, status=400)
    except Exception as e:
        print(f"Unexpected error in batch upload: {e}")
        traceback.print_exc()
        return JsonResponse({
            'error': str(e),
            'status': 'failed'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def batch_status(request, batch_id):
    """
    Check the status of a batch processing job.
    """
    async def get_batch_status(batch_id):
        try:
            temporal_client = await TemporalClient.connect("localhost:7233")
            # In a full implementation, you'd query workflows by batch ID
            # For now, returning a basic response
            return {
                'batch_id': batch_id,
                'status': 'processing',
                'message': 'Check Temporal UI for detailed status',
                'temporal_ui': f'http://localhost:8080'
            }
        except Exception as e:
            return {
                'batch_id': batch_id,
                'status': 'error',
                'message': str(e)
            }
    
    try:
        status = async_to_sync(get_batch_status)(batch_id)
        return JsonResponse(status)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Add a test endpoint to verify the setup
@csrf_exempt
def test_temporal_connection(request):
    """Test endpoint to verify Temporal connection"""
    
    async def test_connection():
        try:
            client = await TemporalClient.connect("localhost:7233")
            return True, "Connected successfully"
        except Exception as e:
            return False, str(e)
    
    success, message = async_to_sync(test_connection)()
    
    status = {
        "temporal_connected": success,
        "temporal_message": message,
        "supabase_url_set": bool(settings.SUPABASE_URL),
        "supabase_key_set": bool(settings.SUPABASE_SERVICE_KEY),
    }
    
    return HttpResponse(json.dumps(status, indent=2), content_type="application/json")