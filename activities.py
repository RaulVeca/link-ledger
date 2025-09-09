import os
import json
import tempfile
from typing import Dict, Any
from datetime import datetime

# Import temporalio activity module
from temporalio import activity

from supabase import create_client, Client
from doctr.io import DocumentFile
from doctr.models import ocr_predictor

#from file_handler.services.invoice_extraction import InvoiceExtractor


# Define the custom exception class
class FileProcessingError(Exception):
    """Custom exception for file processing errors"""
    pass


# Use the decorator directly with explicit name
@activity.defn(name="process_file_activity")
async def process_file_activity(args: dict) -> str:
    """
    Process a file by downloading it from Supabase, running OCR, and uploading results.
    
    Args:
        args: Dictionary containing:
            - filename: Name of the file to process
            - bucket_name: Supabase bucket name
            - supabase_url: Supabase project URL
            - supabase_key: Supabase service key
            
    Returns:
        Success message with processing details
        
    Raises:
        FileProcessingError: If any step in the processing fails
    """
    # Extract arguments CORRECTLY - they come as a dict with these keys
    filename = args.get("filename")
    bucket_name = args.get("bucket_name")
    supabase_url = args.get("supabase_url")
    supabase_key = args.get("supabase_key")
    
    # Validate required arguments
    if not all([filename, bucket_name, supabase_url, supabase_key]):
        activity.logger.error(f"Missing required arguments. Got: filename={filename}, bucket={bucket_name}")
        raise FileProcessingError(f"Missing required arguments for file processing. Received args: {list(args.keys())}")
    
    # Start timing
    activity.logger.info(f"Starting processing for file: {filename}")
    start_time = datetime.now()
    
    # Initialize Supabase client
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        activity.logger.info("Supabase client initialized successfully")
    except Exception as e:
        activity.logger.error(f"Failed to initialize Supabase client: {e}")
        raise FileProcessingError(f"Supabase initialization failed: {str(e)}")
    
    # Download the file from Supabase storage
    activity.logger.info(f"Downloading {filename} from bucket {bucket_name}...")
    try:
        file_content = supabase.storage.from_(bucket_name).download(filename)
        file_size_mb = len(file_content) / (1024 * 1024)
        activity.logger.info(f"File downloaded successfully ({file_size_mb:.2f} MB)")
    except Exception as e:
        activity.logger.error(f"Error downloading file: {e}")
        raise FileProcessingError(f"Failed to download file: {str(e)}")
    
    # Validate file content
    if not file_content:
        raise FileProcessingError("Downloaded file is empty")
    
    # Process with doctr-OCR
    activity.logger.info("INITIALIZING doctr OCR model...")
    try:
        # Initialize the OCR model (this might take a moment on first run)
        model = ocr_predictor(pretrained=True)
        activity.logger.info("OCR MODEL loaded successfully")
    except Exception as e:
        activity.logger.error(f"Failed to initialize OCR model: {e}")
        raise FileProcessingError(f"OCR model initialization failed: {str(e)}")
    
    # Process the document
    activity.logger.info("PROCESSING DOCUMENT WITH OCR...")
    try:
        # Create document from PDF content
        activity.logger.debug("Creating DocumentFile from PDF...")
        doc = DocumentFile.from_pdf(file_content)
        activity.logger.debug(f"Document created successfully. Type: {type(doc)}")
        
        # Run OCR on the document
        activity.logger.info("Running OCR model on document...")
        result = model(doc)
        activity.logger.info("OCR processing complete")
        
        # Export results to JSON format
        json_output = result.export()
        
        # Add metadata to the output
        json_output['metadata'] = {
            'original_filename': filename,
            'processing_timestamp': datetime.now().isoformat(),
            'file_size_bytes': len(file_content),
            'processor': 'doctr',
            'processing_duration_seconds': (datetime.now() - start_time).total_seconds()
        }
        
        # Debug: Log output size
        json_data = json.dumps(json_output, indent=2).encode('utf-8')
        activity.logger.info(f"DOCUMENT PROCESSING COMPLETE. Output size: {len(json_data)} bytes")
        
    except Exception as e:
        activity.logger.error(f"ERROR DURING OCR PROCESSING: {e}")
        activity.logger.error(f"Error type: {type(e).__name__}")
        activity.logger.error(f"Error details: {str(e)}")
        raise FileProcessingError(f"OCR PROCESSING FAILED: {str(e)}")
    
    # Prepare output filename and path
    base_name = os.path.splitext(os.path.basename(filename))[0]
    json_file_name = f"{base_name}.json"
    json_file_path = f"json-output/{json_file_name}"
    
    # Upload JSON result to Supabase
    activity.logger.info(f"Uploading JSON output to {json_file_path}...")
    try:
        # Upload with appropriate content type
        upload_result = supabase.storage.from_(bucket_name).upload(
            path=json_file_path,
            file=json_data,
            file_options={
                "content-type": "application/json",
                "cache-control": "max-age=3600",
                "upsert": "true"  # Overwrite if exists
            }
        )
        
        activity.logger.info("JSON output uploaded successfully")
        
    except Exception as e:
        activity.logger.error(f"Error uploading JSON result: {e}")
        # Check if it's because the file already exists
        if "already exists" in str(e).lower():
            activity.logger.warning("Output file already exists, attempting to update...")
            try:
                # Try to update instead
                update_result = supabase.storage.from_(bucket_name).update(
                    path=json_file_path,
                    file=json_data,
                    file_options={"content-type": "application/json"}
                )
                activity.logger.info("JSON output updated successfully")
            except Exception as update_error:
                raise FileProcessingError(f"Failed to update existing file: {str(update_error)}")
        else:
            raise FileProcessingError(f"Failed to upload JSON result: {str(e)}")
    
    # Calculate processing time
    processing_time = (datetime.now() - start_time).total_seconds()
    
    # Return success message with details
    return (f"Successfully processed {filename}. "
            f"Processing time: {processing_time:.2f} seconds. "
            f"Output saved to: {json_file_path}")