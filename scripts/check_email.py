import sys
import os

# Dodaj ścieżkę do katalogu głównego projektu
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from flask_mail import Message
from extensions import mail
import traceback

def test_email(recipient):
    app = create_app()
    with app.app_context():
        print(f"Próba wysłania maila testowego na adres: {recipient}")
        print(f"Serwer SMTP: {app.config['MAIL_SERVER']}")
        print(f"Port SMTP: {app.config['MAIL_PORT']}")
        print(f"Użytkownik: {app.config['MAIL_USERNAME']}")
        
        try:
            msg = Message(
                subject="Test konfiguracji email - Kable",
                recipients=[recipient],
                body="To jest wiadomość testowa z systemu Kable. Jeśli ją widzisz, konfiguracja email działa poprawnie.",
                sender=app.config['MAIL_DEFAULT_SENDER']
            )
            mail.send(msg)
            print("\nSUKCES: Wiadomość została wysłana pomyślnie!")
        except Exception as e:
            print(f"\nBŁĄD: Nie udało się wysłać maila.")
            print(f"Szczegóły błędu: {str(e)}")
            print("\nPełny traceback:")
            print(traceback.format_exc())

if __name__ == "__main__":
    if len(sys.argv) > 1:
        recipient = sys.argv[1]
    else:
        recipient = input("Podaj adres email do testu: ")
    
    test_email(recipient)
