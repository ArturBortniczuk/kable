from app import app, db
from models import CableResponse

def cleanup_invalid_responses():
    with app.app_context():
        try:
            # Znajdź odpowiedzi z NULL w wymaganych polach
            invalid_responses = CableResponse.query.filter(
                db.or_(
                    CableResponse.delivery_date_start == None,
                    CableResponse.delivery_date_end == None,
                    CableResponse.validity_date == None
                )
            ).all()

            # Wyświetl informacje o znalezionych rekordach
            print(f"Znaleziono {len(invalid_responses)} nieprawidłowych odpowiedzi")
            
            # Usuń znalezione rekordy
            for response in invalid_responses:
                print(f"Usuwanie odpowiedzi ID: {response.id} dla kabla ID: {response.cable_id}")
                db.session.delete(response)
            
            # Zatwierdź zmiany
            db.session.commit()
            print("Czyszczenie zakończone sukcesem!")

        except Exception as e:
            print(f"Wystąpił błąd podczas czyszczenia: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    cleanup_invalid_responses()