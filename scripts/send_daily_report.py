import sys
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging

# Add project root to sys.path to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from app import create_app
from services.reports import get_weekly_stats
from flask_mail import Message
from extensions import mail
from flask import render_template

# Configure logging
log_dir = os.path.join(project_root, 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    filename=os.path.join(log_dir, 'daily_report.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def send_daily_report():
    app = create_app()
    
    with app.app_context():
        try:
            logging.info("Starting daily report generation...")
            
            # Calculate time range: Monday of current week to Now
            now = datetime.now(ZoneInfo("Europe/Warsaw"))
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            
            logging.info(f"Generating report for period: {start_date} - {end_date}")
            
            stats = get_weekly_stats(start_date=start_date, end_date=end_date)
            
            html_content = render_template(
                'emails/weekly_report.html',
                stats=stats,
                app_url='http://ArturBortniczuk.pythonanywhere.com' 
            )
            
            # Recipients list
            recipients = [
                'm.klewinowski@grupaeltron.pl',
                'j.klewinowski@grupaeltron.pl',
                'a.bortniczuk@grupaeltron.pl'
            ]
            
            subject = f'Raport Tygodniowy Kable: {stats["start_date"].strftime("%d.%m")} - {stats["end_date"].strftime("%d.%m")}'
            
            if len(sys.argv) > 1 and sys.argv[1] == '--dry-run':
                print(f"Subject: {subject}")
                print(f"Recipients: {recipients}")
                print("HTML Content Preview (first 500 chars):")
                print(html_content[:500])
                logging.info("Dry run completed.")
                return

            msg = Message(
                subject=subject,
                recipients=recipients,
                html=html_content
            )
            
            # Send email
            mail.send(msg)
            logging.info(f"Report sent successfully to: {', '.join(recipients)}")
            print(f"Report sent successfully to: {', '.join(recipients)}")

        except Exception as e:
            logging.error(f"Error sending daily report: {str(e)}")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    send_daily_report()
