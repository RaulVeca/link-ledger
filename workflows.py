from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

# Import with pass_through to avoid sandbox restrictions
with workflow.unsafe.imports_passed_through():
    from temporal_app.activities import process_file_activity


@workflow.defn
class FileProcessingWorkflow:
    """
    Workflow that orchestrates file processing with OCR.
    
    This workflow:
    1. Receives file information
    2. Executes the OCR processing activity
    3. Returns the result
    """
    
    @workflow.run
    async def run(self, filename: str, bucket_name: str, supabase_url: str, supabase_key: str) -> str:
        """
        Main workflow execution method.
        
        Args:
            filename: Name of the file to process
            bucket_name: Supabase bucket name
            supabase_url: Supabase project URL
            supabase_key: Supabase service key
            
        Returns:
            Success message with processing details
        """
        workflow.logger.info(f"Starting FileProcessingWorkflow for file: {filename}")
        
        # Prepare activity arguments
        activity_args = {
            "filename": filename,
            "bucket_name": bucket_name,
            "supabase_url": supabase_url,
            "supabase_key": supabase_key,
        }
        
        workflow.logger.info(f"Executing process_file_activity for {filename}")
        
        try:
            # Execute the activity with proper timeout and retry policy
            result = await workflow.execute_activity(
                process_file_activity,
                activity_args,
                start_to_close_timeout=timedelta(minutes=10),  # Increased timeout for large files
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                    backoff_coefficient=2,
                ),
            )
            
            workflow.logger.info(f"Successfully processed {filename}")
            return result
            
        except Exception as e:
            workflow.logger.error(f"Failed to process {filename}: {e}")
            raise