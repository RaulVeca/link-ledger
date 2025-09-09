#!/usr/bin/env python
"""
Multi-priority worker runner for handling different processing priorities.
Save this as temporal_app/run_priority_workers.py
"""

import asyncio
import sys
import os
import logging
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from temporalio.client import Client
from temporalio.worker import Worker
from temporal_app.activities import process_file_activity
from temporal_app.workflows import FileProcessingWorkflow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_worker(task_queue: str, max_concurrent: int, worker_name: str):
    """Run a single worker for a specific task queue"""
    
    logger.info(f"Starting {worker_name} worker...")
    logger.info(f"  Task Queue: {task_queue}")
    logger.info(f"  Max Concurrent Activities: {max_concurrent}")
    
    try:
        # Connect to Temporal
        client = await Client.connect("localhost:7233")
        
        # Create and run worker
        worker = Worker(
            client,
            task_queue=task_queue,
            workflows=[FileProcessingWorkflow],
            activities=[process_file_activity],
            max_concurrent_activities=max_concurrent,
            max_concurrent_workflow_tasks=10,
        )
        
        logger.info(f"[SUCCESS] {worker_name} worker started and listening...")
        await worker.run()
        
    except Exception as e:
        logger.error(f"[ERROR] {worker_name} worker failed: {e}")
        raise


async def main():
    """Run multiple workers for different priority queues"""
    
    print("="*60)
    print("MULTI-PRIORITY TEMPORAL WORKERS")
    print("="*60)
    
    # Define worker configurations
    # High priority: more concurrent activities
    # Low priority: fewer concurrent activities
    workers = [
        {
            "name": "High Priority",
            "queue": "file-processing-high-priority",
            "max_concurrent": 10
        },
        {
            "name": "Normal Priority",
            "queue": "file-processing-task-queue",
            "max_concurrent": 5
        },
        {
            "name": "Low Priority",
            "queue": "file-processing-low-priority",
            "max_concurrent": 2
        }
    ]
    
    # Create tasks for all workers
    tasks = []
    for worker_config in workers:
        task = asyncio.create_task(
            run_worker(
                task_queue=worker_config["queue"],
                max_concurrent=worker_config["max_concurrent"],
                worker_name=worker_config["name"]
            )
        )
        tasks.append(task)
    
    print(f"Starting {len(workers)} workers with different priorities...")
    print("High priority files will be processed faster!")
    print("\nWorkers running. Press Ctrl+C to stop all workers.")
    print("="*60)
    
    try:
        # Wait for all workers (they run indefinitely)
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down all workers...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        print("[SUCCESS] All workers stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Workers stopped by user")