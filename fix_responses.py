from app import app, db
from models import Query, Cable, CableResponse
from datetime import datetime
from zoneinfo import ZoneInfo
import sqlite3

def fix_responses():
    with app.app_context():
        print("\n=== NAPRAWA ODPOWIEDZI ===")
        
        db_path = '/home/ArturBortniczuk/myapp/instance/queries.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Najpierw pobierz wszystkie odpowiedzi, które mają datę w komentarzach
        cursor.execute("""
            SELECT id, comments, price_per_meter_client, cable_id
            FROM cable_response
            WHERE comments LIKE '2024-%'
        """)
        responses = cursor.fetchall()
        
        print(f"Znaleziono {len(responses)} odpowiedzi do naprawy")
        
        for resp in responses:
            try:
                resp_id = resp[0]
                date_str = resp[1]  # Data jest w komentarzach
                
                # Konwertuj string daty na obiekt datetime
                try:
                    date_responded = datetime.strptime(date_str.strip(), '%Y-%m-%d %H:%M:%S.%f')
                    date_responded = date_responded.replace(tzinfo=ZoneInfo("Europe/Warsaw"))
                except Exception as e:
                    print(f"Błąd konwersji daty dla ID {resp_id}: {str(e)}")
                    continue
                
                # Aktualizuj odpowiedź
                cursor.execute("""
                    UPDATE cable_response
                    SET date_responded = ?,
                        comments = NULL
                    WHERE id = ?
                """, (date_responded, resp_id))
                
                print(f"Naprawiono odpowiedź ID: {resp_id}")
            
            except Exception as e:
                print(f"Błąd przy odpowiedzi ID {resp_id}: {str(e)}")
                continue
        
        # Zatwierdź zmiany
        try:
            conn.commit()
            print("\nZmiany zostały zapisane pomyślnie!")
        except Exception as e:
            print(f"Błąd podczas zapisywania zmian: {str(e)}")
            conn.rollback()
        finally:
            conn.close()

if __name__ == '__main__':
    fix_responses()