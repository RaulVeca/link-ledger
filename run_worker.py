#!/usr/bin/env python
import asyncio
import logging
import sys
import os
import signal
from typing import Optional
from datetime import datetime

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Path setup - keep this if your module structure requires it
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from temporalio.client import Client
from temporalio.worker import Worker

# Import your workflows and activities
from temporal_app.activities import process_file_activity
from temporal_app.workflows import FileProcessingWorkflow

# Enhanced logging configuration
def setup_logging(debug_mode: bool = False):
    """Configure logging with optional debug mode"""
    log_level = logging.DEBUG if debug_mode else logging.INFO
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Log filename with timestamp
    log_filename = f'logs/temporal_worker_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    # Configure handlers with UTF-8 encoding
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    console_handler = logging.StreamHandler(sys.stdout)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        handlers=[console_handler, file_handler]
    )
    
    # Set specific loggers if needed
    if debug_mode:
        logging.getLogger('temporalio').setLevel(logging.DEBUG)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Log file: {log_filename}")
    logger.info(f"Debug mode: {'ON' if debug_mode else 'OFF'}")
    
    return logger


# Global logger
logger = setup_logging(debug_mode=os.getenv('DEBUG', 'false').lower() == 'true')


class GracefulShutdown:
    """Handle graceful shutdown of the worker"""
    def __init__(self):
        self.shutdown_requested = False
        
    def request_shutdown(self, signum, frame):
        logger.info(f"Received signal {signum}. Requesting graceful shutdown...")
        self.shutdown_requested = True


async def create_temporal_client(temporal_host: str = "localhost:7233", max_retries: int = 3) -> Optional[Client]:
    """
    Create Temporal client with retry logic
    
    Args:
        temporal_host: The Temporal server address
        max_retries: Maximum number of connection attempts
    
    Returns:
        Temporal Client or None if connection fails
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Connecting to Temporal server at {temporal_host}... (Attempt {attempt}/{max_retries})")
            
            # You can add TLS configuration here if needed
            client = await Client.connect(
                temporal_host,
                # tls=True,  # Uncomment for TLS
                # namespace="default",  # Specify namespace if not default
            )
            
            logger.info("[SUCCESS] SUCCESSFULLY CONNECTED TO TEMPORAL SERVER")
            
            # Test the connection by getting worker build id
            try:
                # This is a simple health check
                await client.workflow_service.get_system_info({})
                logger.info("[SUCCESS] Temporal server health check passed")
            except Exception as health_error:
                logger.warning(f"Health check failed: {health_error}")
            
            return client
            
        except Exception as e:
            logger.error(f"[ERROR] Connection attempt {attempt} failed: {e}")
            
            if attempt < max_retries:
                wait_time = attempt * 2  # Exponential backoff
                logger.info(f"Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"[ERROR] FAILED TO CONNECT TO TEMPORAL SERVER after {max_retries} attempts")
                
    return None


async def verify_imports():
    """Verify that all required modules are properly imported"""
    logger.info("Verifying imports...")
    
    try:
        # Check workflow import
        logger.info(f"[OK] FileProcessingWorkflow imported: {FileProcessingWorkflow.__name__}")
        
        # Check activity import - handle different temporalio versions
        if hasattr(process_file_activity, '_defn'):
            # Older temporalio versions
            logger.info(f"[OK] process_file_activity imported and decorated: {process_file_activity._defn.name}")
            return True
        elif hasattr(process_file_activity, '__temporal_activity_definition'):
            # Newer temporalio versions (1.15.0+)
            logger.info(f"[OK] process_file_activity imported and decorated (v1.15.0+ style)")
            logger.info(f"         Function name: {process_file_activity.__name__}")
            return True
        elif callable(process_file_activity):
            # Activity is imported but might not be decorated
            logger.warning(f"[WARNING] process_file_activity may not be decorated properly")
            logger.warning(f"         Function name: {process_file_activity.__name__}")
            logger.warning(f"         Attributes: {[a for a in dir(process_file_activity) if 'temporal' in a.lower()]}")
            
            # Check for any temporal-related attributes
            temporal_attrs = [a for a in dir(process_file_activity) if 'temporal' in a.lower() or '_defn' in a]
            if temporal_attrs:
                logger.info(f"[OK] Found temporal attributes: {temporal_attrs}")
                logger.info("[INFO] Activity appears to be decorated (new format)")
                return True
            else:
                logger.error("[ERROR] No temporal decoration found on activity")
                return False
        else:
            logger.error("[ERROR] process_file_activity is not a callable function")
            return False
            
    except Exception as e:
        logger.error(f"[ERROR] Import verification failed: {e}")
        logger.error(f"        Error type: {type(e).__name__}")
        return False


async def main():
    """Main worker function"""
    
    # Configuration (can be environment variables)
    TASK_QUEUE = os.getenv("TEMPORAL_TASK_QUEUE", "file-processing-task-queue")
    TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")
    NAMESPACE = os.getenv("TEMPORAL_NAMESPACE", "default")
    WORKER_ID = os.getenv("WORKER_ID", f"worker-{os.getpid()}")
    
    logger.info("=" * 60)
    logger.info("TEMPORAL WORKER STARTING")
    logger.info("=" * 60)
    logger.info(f"Worker ID: {WORKER_ID}")
    logger.info(f"Task Queue: {TASK_QUEUE}")
    logger.info(f"Temporal Host: {TEMPORAL_HOST}")
    logger.info(f"Namespace: {NAMESPACE}")
    logger.info(f"Process ID: {os.getpid()}")
    logger.info("=" * 60)
    
    # Verify imports before starting
    if not await verify_imports():
        logger.error("Import verification failed. Please check your module structure.")
        sys.exit(1)
    
    # Create client connection with retries
    client = await create_temporal_client(TEMPORAL_HOST)
    if not client:
        logger.error("Could not establish connection to Temporal server. Exiting.")
        sys.exit(1)
    
    # Setup graceful shutdown
    shutdown_handler = GracefulShutdown()
    signal.signal(signal.SIGINT, shutdown_handler.request_shutdown)
    signal.signal(signal.SIGTERM, shutdown_handler.request_shutdown)
    
    try:
        # Create the worker
        worker = Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[FileProcessingWorkflow],
            activities=[process_file_activity],
            # Optional configurations
            max_concurrent_activities=10,  # Limit concurrent activities
            max_concurrent_workflow_tasks=10,  # Limit concurrent workflow tasks
            # identity=WORKER_ID,  # Custom worker identity
        )
        
        logger.info("=" * 60)
        logger.info(f"[SUCCESS] Worker successfully created")
        logger.info(f"         Task Queue: {TASK_QUEUE}")
        logger.info(f"         Registered Workflows: {[w.__name__ for w in [FileProcessingWorkflow]]}")
        
        # Handle activity name display for different temporalio versions
        activity_names = []
        for activity in [process_file_activity]:
            if hasattr(activity, '_defn'):
                # Older versions
                activity_names.append(activity._defn.name)
            elif hasattr(activity, '__temporal_activity_definition'):
                # Newer versions (1.15.0+)
                activity_names.append(activity.__name__)
            else:
                activity_names.append(activity.__name__)
        
        logger.info(f"         Registered Activities: {activity_names}")
        logger.info(f"         Worker is ready and waiting for tasks...")
        logger.info("=" * 60)
        
        # Create a task for the worker
        worker_task = asyncio.create_task(worker.run())
        
        # Monitor for shutdown
        while not shutdown_handler.shutdown_requested:
            # Check if worker task is still running
            if worker_task.done():
                # Worker stopped unexpectedly
                exception = worker_task.exception()
                if exception:
                    logger.error(f"Worker task failed: {exception}")
                    raise exception
                else:
                    logger.info("Worker task completed")
                    break
            
            # Brief sleep to prevent busy waiting
            await asyncio.sleep(1)
        
        if shutdown_handler.shutdown_requested:
            logger.info("Shutdown requested, stopping worker...")
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                logger.info("Worker task cancelled successfully")
        
    except KeyboardInterrupt:
        logger.info("[WARNING] Worker shutdown requested via keyboard interrupt")
    except asyncio.CancelledError:
        logger.info("[INFO] Worker task was cancelled")
    except Exception as e:
        logger.error(f"[ERROR] Worker encountered an error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Cleaning up...")
        if client:
            # Client doesn't need explicit cleanup in current versions
            pass
        logger.info("[SUCCESS] Worker shutdown complete")


async def health_check():
    """Standalone health check function"""
    TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")
    
    try:
        client = await Client.connect(TEMPORAL_HOST)
        await client.workflow_service.get_system_info({})
        print("[SUCCESS] Temporal server is healthy")
        return True
    except Exception as e:
        print(f"[ERROR] Temporal server health check failed: {e}")
        return False


if __name__ == "__main__":
    # Check for special commands
    if len(sys.argv) > 1 and sys.argv[1] == "health":
        # Run health check only
        asyncio.run(health_check())
    else:
        # Run the worker
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\n[WARNING] Worker stopped by user")
        except Exception as e:
            logger.error(f"[FATAL] Fatal error: {e}", exc_info=True)
            sys.exit(1)