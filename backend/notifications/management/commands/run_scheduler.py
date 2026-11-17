import threading

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.core.management.base import BaseCommand

from notifications.scheduler import (
    notify_salespersons_daily_followups,
    remind_surveys_scheduled_tomorrow,
)


class Command(BaseCommand):
    help = "Starts APScheduler (BlockingScheduler, Asia/Kolkata) for Solar CRM reminders."

    def add_arguments(self, parser):
        parser.add_argument(
            '--duration',
            type=int,
            default=0,
            help='Run the scheduler for a specified number of seconds and then cleanly shut down (useful for testing/verification).',
        )
        parser.add_argument(
            '--run-now',
            action='store_true',
            help='Run both scheduled reminder jobs once immediately on startup before listening.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Initializing Solar CRM APScheduler (Asia/Kolkata)..."))

        scheduler = BlockingScheduler(timezone="Asia/Kolkata")

        # Job 1: Daily at 9:00 AM Asia/Kolkata
        scheduler.add_job(
            notify_salespersons_daily_followups,
            trigger=CronTrigger(hour=9, minute=0, timezone="Asia/Kolkata"),
            id='daily_followup_reminder',
            name='Daily Salesperson Follow-up Reminder',
            replace_existing=True,
        )

        # Job 2: Daily at 18:00 (6:00 PM) Asia/Kolkata
        scheduler.add_job(
            remind_surveys_scheduled_tomorrow,
            trigger=CronTrigger(hour=18, minute=0, timezone="Asia/Kolkata"),
            id='daily_survey_reminder',
            name='Daily Survey Tomorrow Reminder',
            replace_existing=True,
        )

        self.stdout.write("Configured jobs:")
        for job in scheduler.get_jobs():
            self.stdout.write(f"  - [{job.id}] {job.name} -> {job.trigger}")

        # Optional immediate execution
        if options['run_now']:
            self.stdout.write("\nExecuting immediate run of scheduled jobs...")
            notifs = notify_salespersons_daily_followups()
            self.stdout.write(f"  Follow-up reminders generated: {len(notifs)} notifications")
            survey_res = remind_surveys_scheduled_tomorrow()
            self.stdout.write(f"  Survey reminders processed: {survey_res['surveys_processed']} surveys, {survey_res['messages_sent']} WhatsApp messages sent")

        # Auto-shutdown timer if duration specified
        duration = options['duration']
        if duration > 0:
            self.stdout.write(f"Scheduler will run for {duration} seconds and then exit cleanly.")
            timer = threading.Timer(duration, scheduler.shutdown, args=[False])
            timer.daemon = True
            timer.start()

        self.stdout.write(self.style.SUCCESS("Scheduler is running. Press Ctrl+C to exit.\n"))
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.stdout.write(self.style.WARNING("\nScheduler stopped."))
