import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from app.config import settings
from app.email_processor import process_all_users_background

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
    
    def start(self):
        """Start the email processing scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        # Add job to process emails periodically
        self.scheduler.add_job(
            func=self._process_emails_job,
            trigger=IntervalTrigger(minutes=settings.check_interval_minutes),
            id='email_processing',
            name='Process emails for all users',
            replace_existing=True,
            max_instances=1  # Prevent overlapping executions
        )
        
        self.scheduler.start()
        self.is_running = True
        logger.info(f"Email scheduler started - checking every {settings.check_interval_minutes} minutes")
    
    def stop(self):
        """Stop the email processing scheduler"""
        if not self.is_running:
            return
        
        self.scheduler.shutdown()
        self.is_running = False
        logger.info("Email scheduler stopped")
    
    def _process_emails_job(self):
        """The actual job that processes emails"""
        logger.info("Starting scheduled email processing...")
        start_time = datetime.utcnow()
        
        try:
            results = process_all_users_background()
            
            # Log summary
            total_emails = sum(r.get('emails_processed', 0) for r in results)
            total_packages = sum(r.get('packages_found', 0) for r in results)
            total_errors = sum(len(r.get('errors', [])) for r in results)
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"Email processing completed in {duration:.2f}s")
            logger.info(f"Processed {total_emails} emails, found {total_packages} packages, {total_errors} errors")
            
            if total_errors > 0:
                for result in results:
                    if result.get('errors'):
                        logger.error(f"Errors for user {result['user_email']}: {result['errors']}")
        
        except Exception as e:
            logger.error(f"Error in scheduled email processing: {e}")
    
    def trigger_immediate_processing(self):
        """Trigger immediate email processing for all users"""
        logger.info("Triggering immediate email processing...")
        self.scheduler.add_job(
            func=self._process_emails_job,
            trigger='date',
            run_date=datetime.utcnow(),
            id='immediate_email_processing',
            replace_existing=True
        )
    
    def get_status(self) -> dict:
        """Get scheduler status"""
        jobs = []
        if self.is_running:
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None
                })
        
        return {
            'running': self.is_running,
            'jobs': jobs,
            'check_interval_minutes': settings.check_interval_minutes
        }

# Global scheduler instance
email_scheduler = EmailScheduler()