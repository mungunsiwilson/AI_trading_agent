"""Scheduler - Runs the pipeline on a schedule (daily at 9 AM China time)."""
import logging
import schedule
import time
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import config

logger = logging.getLogger(__name__)

def run_pipeline():
    """Execute the main pipeline."""
    logger.info("Scheduled pipeline execution triggered...")
    
    try:
        from main import DouyinOpportunityPipeline
        
        pipeline = DouyinOpportunityPipeline()
        results = pipeline.run()
        
        if results['success']:
            logger.info("✓ Scheduled pipeline completed successfully")
        else:
            logger.error(f"✗ Scheduled pipeline failed: {results['errors']}")
            
    except Exception as e:
        logger.error(f"Scheduled pipeline execution failed: {e}", exc_info=True)

def start_scheduler():
    """Start the scheduler to run pipeline daily at configured time."""
    # Parse schedule time (default: 09:00 Asia/Shanghai)
    schedule_time = config.schedule_time  # "09:00"
    timezone = config.timezone  # "Asia/Shanghai"
    
    logger.info(f"Starting scheduler for {schedule_time} {timezone}")
    logger.info(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Schedule daily job
    schedule.every().day.at(schedule_time).do(run_pipeline)
    
    logger.info(f"Next run scheduled for: {schedule.get_next_run()}")
    print(f"\n✓ Scheduler started. Next run: {schedule.get_next_run()}")
    print(f"  Time: {schedule_time} {timezone}")
    print("  Press Ctrl+C to stop\n")
    
    # Run pending jobs immediately if any
    schedule.run_pending()
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    # Setup basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        start_scheduler()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
