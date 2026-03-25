"""
Scheduler module for automated daily execution.
Supports both cron jobs and OpenClaw scheduling.
"""

import asyncio
import logging
import schedule
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
import pytz

from config import Config
from main import OpportunityFinderPipeline


logger = logging.getLogger(__name__)


class PipelineScheduler:
    """
    Scheduler for running the opportunity finder pipeline.
    
    Supports:
    - Cron-based scheduling (Linux/Unix)
    - Python schedule library (cross-platform)
    - OpenClaw integration (when available)
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.pipeline = OpportunityFinderPipeline(self.config)
        self.timezone = pytz.timezone(self.config.timezone)
        
        logger.info(f"PipelineScheduler initialized with timezone: {self.config.timezone}")
    
    def run_job(self):
        """Execute the pipeline job."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Scheduled job started at: {datetime.now(self.timezone)}")
        logger.info(f"{'='*60}\n")
        
        try:
            # Run the async pipeline
            report = asyncio.run(self.pipeline.run_pipeline())
            
            logger.info(f"\nJob completed successfully")
            
            # Send notification (placeholder - implement based on your needs)
            self.send_notification(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Job failed: {e}", exc_info=True)
            self.send_error_notification(str(e))
            return None
    
    def send_notification(self, report: str):
        """
        Send report notification via configured channel.
        
        Implementations:
        - Email (SMTP)
        - Slack webhook
        - Telegram bot
        - OpenClaw sessions_send
        
        This is a placeholder - customize based on your needs.
        """
        # TODO: Implement actual notification delivery
        # Examples:
        
        # 1. Email via SMTP
        # import smtplib
        # from email.mime.text import MIMEText
        # msg = MIMEText(report)
        # msg['Subject'] = 'Douyin Opportunity Report'
        # ... send via SMTP ...
        
        # 2. Slack webhook
        # import requests
        # requests.post(SLACK_WEBHOOK_URL, json={'text': report})
        
        # 3. Telegram bot
        # import requests
        # requests.post(f'https://api.telegram.org/bot{TOKEN}/sendMessage', 
        #              json={'chat_id': CHAT_ID, 'text': report})
        
        # 4. OpenClaw sessions_send (if available)
        # if self.config.openclaw_enabled:
        #     from openclaw import OpenClaw
        #     oc = OpenClaw(api_key=self.config.openclaw_api_key)
        #     oc.sessions_send(content=report)
        
        logger.info("Notification sent (placeholder implementation)")
    
    def send_error_notification(self, error_message: str):
        """Send error notification."""
        error_report = f"""# ⚠️ Pipeline Error Alert

**Time:** {datetime.now(self.timezone).isoformat()}
**Error:** {error_message}

Please check logs at: {self.config.log_file_path}
"""
        # Similar to send_notification but for errors
        logger.error(f"Error notification: {error_message}")
    
    def schedule_daily(self, hour: int = None, minute: int = None):
        """
        Schedule pipeline to run daily at specified time.
        
        Args:
            hour: Hour in configured timezone (default: from config).
            minute: Minute (default: from config).
        """
        hour = hour or self.config.schedule_hour
        minute = minute or self.config.schedule_minute
        
        schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(self.run_job)
        
        logger.info(f"Scheduled daily run at {hour:02d}:{minute:02d} {self.config.timezone}")
    
    def start(self, blocking: bool = True):
        """
        Start the scheduler.
        
        Args:
            blocking: If True, block and run indefinitely. If False, return immediately.
        """
        logger.info("Starting scheduler...")
        
        if blocking:
            try:
                while True:
                    schedule.run_pending()
                    time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
        else:
            # Non-blocking mode
            import threading
            thread = threading.Thread(target=self._run_scheduler_loop, daemon=True)
            thread.start()
            logger.info("Scheduler started in background thread")
    
    def _run_scheduler_loop(self):
        """Internal method for background thread execution."""
        while True:
            schedule.run_pending()
            time.sleep(60)


def create_cron_expression(hour: int = 9, minute: int = 0) -> str:
    """
    Generate cron expression for daily execution.
    
    Args:
        hour: Hour (0-23).
        minute: Minute (0-59).
        
    Returns:
        Cron expression string.
    """
    return f"{minute} {hour} * * *"


def setup_openclaw_cron(config: Config) -> str:
    """
    Generate OpenClaw cron setup commands.
    
    Args:
        config: Configuration object.
        
    Returns:
        Shell command string for setting up cron.
    """
    hour = config.schedule_hour
    minute = config.schedule_minute
    
    # Get absolute path to main.py
    script_path = Path(__file__).parent / "main.py"
    script_path = script_path.resolve()
    
    # Create cron command
    cron_expr = f"{minute} {hour} * * *"
    python_cmd = f"cd {Path(__file__).parent} && python {script_path}"
    
    cron_command = f"""
# Add this to crontab using: crontab -e
# Or use OpenClaw: openclaw cron add "{python_cmd}" --schedule="{cron_expr}"

{cron_expr} cd {Path(__file__).parent} && /usr/bin/env python {script_path} >> {config.log_file_path} 2>&1
"""
    
    return cron_command.strip()


def main():
    """Main entry point for scheduler."""
    config = Config()
    scheduler = PipelineScheduler(config)
    
    # Schedule daily run
    scheduler.schedule_daily()
    
    print(f"\nScheduler configured for daily runs at {config.schedule_hour:02d}:{config.schedule_minute:02d} {config.timezone}")
    print("Press Ctrl+C to stop\n")
    
    # Start scheduler (blocking)
    scheduler.start(blocking=True)


if __name__ == "__main__":
    main()
