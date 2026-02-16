from flask import session, flash, redirect, url_for, request, render_template, current_app
from functools import wraps
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask_mail import Message
import pandas as pd
import json
import traceback
import os
from config import config
from extensions import mail
from models import User

# Globalne zmienne dla danych z Excela
markets_data = {}
salespersons_data = {}
email_mapping = {}

def calculate_delivery_dates(option):
    today = datetime.now(ZoneInfo("Europe/Warsaw"))

    if option in ['zielonka', 'bialystok', 'depozyt']:
        # Dla opcji magazynowych zwracamy dzisiejszą datę jako początek i koniec
        return today.date(), today.date()

    # Dla opcji z dniami roboczymi
    try:
        days = int(str(option).replace('dni', '')) # Cast to str to be safe
    except ValueError:
        days = 0 
        
    delivery_date = today
    business_days = 0

    while business_days < days:
        delivery_date += timedelta(days=1)
        if delivery_date.weekday() < 5:  # 0-4 to dni robocze
            business_days += 1

    return today.date(), delivery_date.date()

def calculate_validity_date(option):
    """Oblicza datę ważności oferty na podstawie wybranej opcji"""
    today = datetime.now(ZoneInfo("Europe/Warsaw"))
    try:
        days = int(str(option).replace('dni', ''))
    except ValueError:
        days = 0
    return (today + timedelta(days=days)).date()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Musisz się zalogować, aby uzyskać dostęp do tej strony.', 'warning')
            session['next_url'] = request.url
            return redirect(url_for('auth.login')) # Updated to point to blueprint
        return f(*args, **kwargs)
    return decorated_function

def load_data_from_excel():
    try:
        df = pd.read_excel(config.EXCEL_PATH, header=None)
        salespersons_by_market = {}
        markets = set()
        email_by_name = {}

        for _, row in df.iterrows():
            salesperson = row[0]
            market = row[1]
            email = row[2]

            markets.add(market)

            if market not in salespersons_by_market:
                salespersons_by_market[market] = []
            salespersons_by_market[market].append(salesperson)

            email_by_name[salesperson] = email
            
        # Dodaj użytkowników z bazy danych
        try:
            db_users = User.query.all()
            for user in db_users:
                # Dodaj rynek i handlowca jeśli nie istnieją
                if user.market:
                    markets.add(user.market)
                    if user.market not in salespersons_by_market:
                         salespersons_by_market[user.market] = []
                    if user.username not in salespersons_by_market[user.market]:
                         salespersons_by_market[user.market].append(user.username)
                
                # Dodaj email
                if user.email:
                    email_by_name[user.username] = user.email
                    
        except Exception as e:
            print(f"Błąd podczas ładowania użytkowników z bazy: {str(e)}")

        return sorted(list(markets)), salespersons_by_market, email_by_name
    except Exception as e:
        print(f"Error loading data: {str(e)}") # Using print as current_app might not be available or logger issue
        return [], {}, {}

def init_app_data():
    global markets_data, salespersons_data, email_mapping
    try:
        markets, salespersons, emails = load_data_from_excel()
        markets_data = markets
        salespersons_data = salespersons
        email_mapping = emails
        print("Successfully initialized app data")
    except Exception as e:
        print(f"Error initializing app data: {str(e)}")

def generate_password(name):
    """Generuje hasło z pierwszych trzech liter imienia i nazwiska"""
    parts = name.lower().split()
    if len(parts) >= 2:
        return (parts[0][:3] + parts[-1][:3]).lower()
    return None

def send_new_query_notification(query):
    try:
        print("\n=== Wysyłanie powiadomienia o nowym zapytaniu ===")
        print(f"Zapytanie od: {query.name} dla klienta: {query.client}")

        try:
            print("Próba renderowania szablonu new_query_notification.html...")
            html_content = render_template(
                'emails/new_query_notification.html',
                query=query,
                app_url=request.host_url.rstrip('/')
            )
            print("✓ Szablon wyrenderowany")

            msg = Message(
                subject=f'Nowe zapytanie od {query.name} - {query.client}',
                recipients=['kable@grupaeltron.pl'],
                html=html_content
            )
            print("✓ Wiadomość utworzona")

            print("Próba wysłania maila...")
            mail.send(msg)
            print("✓ Mail wysłany pomyślnie")

        except Exception as e:
            print(f"✗ Błąd: {str(e)}")
            print(f"Traceback:\n{traceback.format_exc()}")

    except Exception as e:
        print(f"✗ Błąd główny: {str(e)}")
        print(f"Traceback:\n{traceback.format_exc()}")

def send_reminder_email(query):
    try:
        current_time = datetime.now(ZoneInfo("Europe/Warsaw"))
        # query.date_submitted is naive in db, but we treat it as Warsaw time
        query_time = query.date_submitted
        if query_time.tzinfo is None:
             query_time = query_time.replace(tzinfo=ZoneInfo("Europe/Warsaw"))
             
        hours_difference = (current_time - query_time).total_seconds() / 3600

        if hours_difference >= 48:
            recipients = ['l.klewinowski@grupaeltron.pl']

            msg = Message(
                subject=f'Przypomnienie o zapytaniu - {query.client}',
                recipients=recipients,
                html=render_template(
                    'emails/reminder_email.html',
                    query=query,
                    hours_passed=int(hours_difference),
                    app_url=request.host_url.rstrip('/')
                )
            )

            mail.send(msg)
            print(f"Sent reminder email for query {query.id} after {int(hours_difference)} hours")
    except Exception as e:
        print(f"Error sending reminder email: {str(e)}")

def send_response_notification(query, responses):
    print("\n=== Rozpoczęcie wysyłania powiadomień ===")
    try:
        # Check if email_mapping is populated, if not try to reload or use init_app_data
        global email_mapping
        if not email_mapping:
            init_app_data()
            
        salesperson_email = email_mapping.get(query.name)
        print(f"Handlowiec: {query.name}")
        print(f"Email handlowca: {salesperson_email}")
        print(f"Klient: {query.client}")

        for cable, response in responses:
            print(f"Kabel: {cable.cable_type}")
            print(f"Cena klienta: {response.price_per_meter_client}")
            print(f"Cena zakupu: {response.price_per_meter_purchase}")

        # Fallback to DB if email not found in mapping
        if not salesperson_email:
            print(f"Email not found in cache for {query.name}, checking database...")
            user = User.query.filter_by(username=query.name).first()
            if user and user.email:
                salesperson_email = user.email
                print(f"Found email in DB: {salesperson_email}")

        if salesperson_email:
            try:
                print(f"\nWysyłanie do handlowca ({salesperson_email})...")
                salesperson_msg = Message(
                    subject=f'Odpowiedź na zapytanie - {query.client}',
                    recipients=[salesperson_email],
                    html=render_template(
                        'emails/response_notification.html',
                        query=query,
                        responses=responses,
                        recipient_type='salesperson'
                    )
                )
                mail.send(salesperson_msg)
                print("✓ Wysłano do handlowca")
            except Exception as e:
                print(f"✗ Błąd wysyłania do handlowca: {str(e)}")
                print(f"Traceback:\n{traceback.format_exc()}")
        else:
            print(f"⚠️ OSTRZEŻENIE: Nie znaleziono adresu email dla handlowca {query.name}. Powiadomienie nie zostało wysłane.")

        print("\nWysyłanie do odbiorcy...")
        logistics_msg = Message(
            subject=f'Kopia: Odpowiedź na zapytanie - {query.client}',
            recipients=['kable@grupaeltron.pl', 'l.sakowicz@grupaeltron.pl'],
            html=render_template(
                'emails/response_notification.html',
                query=query,
                responses=responses,
                recipient_type='logistics'
            )
        )
        mail.send(logistics_msg)
        print("✓ Wysłano do kabli")

    except Exception as e:
        print(f"✗ Błąd główny w send_response_notification: {str(e)}")
        print(f"Traceback:\n{traceback.format_exc()}")
