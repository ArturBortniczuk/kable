import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging

# Dodaj ścieżkę do aplikacji
path = '/home/ArturBortniczuk/myapp'
if path not in sys.path:
    sys.path.append(path)

from app import create_app
from models import Query

logging.basicConfig(
    filename='/home/ArturBortniczuk/myapp/logs/reminders.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def send_daily_reminders():
    app = create_app()
    
    with app.app_context():
        try:
            # Sprawdź tylko nieodpowiedziane zapytania starsze niż 24h
            current_time = datetime.now(ZoneInfo("Europe/Warsaw"))
            deadline = current_time - timedelta(hours=24)
            
            pending_queries = Query.query.filter(
                Query.date_submitted <= deadline
            ).all()

            for query in pending_queries:
                if not query.is_all_responded():
                    hours_waiting = int((current_time - query.date_submitted).total_seconds() / 3600)
                    
                    # Wysyłaj przypomnienie tylko do Łukasza
                    app.notification_service.send_notification(
                        'reminder',
                        {
                            'query': query,
                            'hours_passed': hours_waiting
                        },
                        ['l.sakowicz@grupaeltron.pl']  # tylko jeden odbiorca
                    )
                    logging.info(f"Wysłano przypomnienie dla zapytania {query.id}")

        except Exception as e:
            logging.error(f"Błąd podczas wysyłania przypomnień: {str(e)}")

if __name__ == '__main__':
    send_daily_reminders()