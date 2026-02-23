#!/usr/bin/env python3
"""
ARQ Worker Startup Script
This script starts the ARQ worker for background task processing.
"""

import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.worker import WorkerSettings
from arq import run_worker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Start the ARQ worker."""
    logger.info("Starting ARQ worker for email verification system...")
    try:
        # Use run_worker directly instead of asyncio.run
        run_worker(WorkerSettings)
    except KeyboardInterrupt:
        logger.info("ARQ worker stopped by user")
    except Exception as e:
        logger.error(f"ARQ worker failed: {e}")
        raise

if __name__ == "__main__":
    main()
