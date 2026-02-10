from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from flask_mail import Message
from forms import QueryForm, CableForm, CableResponseForm, ResponseForm, LoginForm, DeleteForm, CommentForm
from extensions import db, mail, csrf
from models import Cable, Query, CableResponse, Comment
from config import config
from flask_wtf import FlaskForm
from functools import wraps
import pandas as pd
import traceback
import json
import os

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
    days = int(option.replace('dni', ''))
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
    days = int(option.replace('dni', ''))
    return (today + timedelta(days=days)).date()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Musisz się zalogować, aby uzyskać dostęp do tej strony.', 'warning')
            session['next_url'] = request.url
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def create_app():
    app = Flask(__name__)
    app.config.from_object(config)
    app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(24)

    # Dodaj te linie
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {'check_same_thread': False},
        'pool_pre_ping': True,
        'pool_recycle': 300
    }

    db.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    return app

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

        return sorted(list(markets)), salespersons_by_market, email_by_name
    except Exception as e:
        app.logger.error(f"Error loading data: {str(e)}")
        return [], {}, {}

def init_app_data():
    global markets_data, salespersons_data, email_mapping
    try:
        markets, salespersons, emails = load_data_from_excel()
        markets_data = markets
        salespersons_data = salespersons
        email_mapping = emails
        app.logger.info("Successfully initialized app data")
    except Exception as e:
        app.logger.error(f"Error initializing app data: {str(e)}")

# Tworzenie aplikacji
app = create_app()

# Inicjalizacja danych przy starcie
with app.app_context():
    init_app_data()

def generate_password(name):
    """Generuje hasło z pierwszych trzech liter imienia i nazwiska"""
    parts = name.lower().split()
    if len(parts) >= 2:
        return (parts[0][:3] + parts[-1][:3]).lower()
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('index'))

    form = LoginForm()
    if request.method == 'POST' and form.validate():
        try:
            df = pd.read_excel(config.EXCEL_PATH, header=None)

            # Specjalne konto admina
            if form.username.data == 'administrator' and form.password.data == 'admin123':
                session['logged_in'] = True
                session['username'] = 'Administrator'
                session['is_admin'] = True
                flash('Zalogowano pomyślnie!', 'success')
                next_url = session.pop('next_url', None)
                return redirect(next_url or url_for('index'))

            if form.username.data == 'superadmin' and form.password.data == 'super123':
                session['logged_in'] = True
                session['username'] = 'SuperAdmin'
                session['is_admin'] = True
                session['can_delete'] = True
                flash('Zalogowano pomyślnie!', 'success')
                next_url = session.pop('next_url', None)
                return redirect(next_url or url_for('index'))

            # Zwykli użytkownicy
            for _, row in df.iterrows():
                name = row[0]
                email = row[2]
                generated_password = generate_password(name)

                if email == form.username.data and generated_password == form.password.data:
                    session['logged_in'] = True
                    session['username'] = name
                    session['email'] = email
                    session['is_admin'] = False
                    session['market'] = row[1]  # Dodaj tę linię
                    flash('Zalogowano pomyślnie!', 'success')

                    next_url = session.pop('next_url', None)
                    return redirect(next_url or url_for('index'))

            flash('Nieprawidłowy email lub hasło.', 'danger')

        except Exception as e:
            print(f"Błąd podczas logowania: {str(e)}")
            flash('Wystąpił błąd podczas logowania.', 'danger')

    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.clear()
    flash('Wylogowano pomyślnie!', 'success')
    return redirect(url_for('login'))

@app.route('/')
def index():
    comment_form = CommentForm()
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    try:
        print("\n=== DIAGNOSTYKA BAZY DANYCH ===")

        # Oblicz datę sprzed tygodnia
        week_ago = datetime.now(ZoneInfo("Europe/Warsaw")) - timedelta(days=7)

        # Podstawowe zapytanie - pobierz zapytania z ostatniego tygodnia
        base_query = Query.query.filter(Query.date_submitted >= week_ago)

        # Pobierz status z parametrów URL
        status = request.args.get('status', 'pending')

        if status == 'answered':
            # Tylko odpowiedziane z ostatniego tygodnia
            queries = [q for q in base_query.all() if q.is_all_responded()]
        elif status == 'pending':
            # Nieodpowiedziane z ostatniego tygodnia + starsze nieodpowiedziane
            older_pending = Query.query.filter(Query.date_submitted < week_ago).all()
            recent_pending = [q for q in base_query.all() if not q.is_all_responded()]
            queries = recent_pending + [q for q in older_pending if not q.is_all_responded()]
        else:
            # Wszystkie z ostatniego tygodnia + starsze nieodpowiedziane
            older_pending = Query.query.filter(Query.date_submitted < week_ago).all()
            queries = base_query.all() + [q for q in older_pending if not q.is_all_responded()]

        # Sortuj po dacie, najnowsze pierwsze
        queries.sort(key=lambda x: x.date_submitted, reverse=True)
        if not queries:
            print("Brak zapytań w bazie danych")
            return render_template('index.html', query_data=[], delete_form=DeleteForm())

        query_data = []
        current_time = datetime.now(ZoneInfo("Europe/Warsaw"))

        for query in queries:
            try:
                print(f"Przetwarzanie zapytania ID: {query.id}")
                query_time = query.date_submitted
                if query_time.tzinfo is None:
                    query_time = query_time.replace(tzinfo=ZoneInfo("Europe/Warsaw"))

                if query.is_all_responded():
                    response_time = query.cables[0].response.date_responded
                    if response_time.tzinfo is None:
                        response_time = response_time.replace(tzinfo=ZoneInfo("Europe/Warsaw"))
                    time_diff = response_time - query_time
                else:
                    time_diff = current_time - query_time

                hours = int(time_diff.total_seconds() // 3600)
                minutes = int((time_diff.total_seconds() % 3600) // 60)
                seconds = int(time_diff.total_seconds() % 60)

                print(f"Przetwarzanie kabli dla zapytania {query.id}")
                cables_info = []
                for cable in query.cables:
                    try:
                        print(f"- Przetwarzanie kabla ID: {cable.id}")
                        cable_info = {
                            'type': cable.cable_type,
                            'length': cable.length,
                            'voltage': cable.voltage,
                            'packaging': cable.packaging,
                            'specific_lengths': cable.specific_lengths,
                            'comments': cable.comments
                        }

                        if cable.response:
                            print(f"  - Znaleziono odpowiedź dla kabla")
                            cable_info['response'] = cable.response
                        else:
                            print(f"  - Brak odpowiedzi dla kabla")
                            cable_info['response'] = None

                        cables_info.append(cable_info)
                    except Exception as cable_error:
                        print(f"Błąd podczas przetwarzania kabla: {str(cable_error)}")
                        raise

                unread_comments_count = db.session.query(Comment).filter(
                    Comment.query_id == query.id,
                    Comment.is_read == False
                ).count()

                query_data.append({
                    'query': query,
                    'cables': cables_info,
                    'time_diff': {
                        'hours': hours,
                        'minutes': minutes,
                        'seconds': seconds
                    },
                    'is_overdue': bool(hours and hours >= 48),
                    'is_responded': query.is_all_responded(),
                    'unread_comments_count': unread_comments_count  # Dodaj to pole
                })

            except Exception as query_error:
                print(f"Błąd podczas przetwarzania zapytania {query.id}: {str(query_error)}")
                print(f"Szczegóły błędu:\n{traceback.format_exc()}")
                raise

        comment_form = CommentForm()  # Utworzenie formularza komentarzy
        return render_template('index.html', query_data=query_data, delete_form=DeleteForm(), comment_form=comment_form)

    except Exception as e:
        print(f"BŁĄD GŁÓWNY w index(): {str(e)}")
        print(f"Pełny traceback:\n{traceback.format_exc()}")
        flash('Wystąpił błąd podczas ładowania danych.', 'error')
        return render_template('index.html', query_data=[], delete_form=DeleteForm())


@app.route('/new-query', methods=['GET', 'POST'])
@login_required
def new_query():
    try:
        print("\n=== DEBUGOWANIE NEW_QUERY ===")
        markets, salespersons_by_market, email_by_name = load_data_from_excel()
        form = QueryForm()

        # Dla zwykłego użytkownika
        if not session.get('is_admin'):
            form.market.choices = [(session.get('market'), session.get('market'))]
            form.name.choices = [(session.get('username'), session.get('username'))]
            form.market.data = session.get('market')
            form.name.data = session.get('username')
        else:
            # Dla admina
            form.market.choices = [('', 'Wybierz rynek')] + [(market, market) for market in markets]
            if request.method == 'POST' and form.market.data:
                form.name.choices = [(name, name) for name in salespersons_by_market.get(form.market.data, [])]
            else:
                form.name.choices = [('', 'Najpierw wybierz rynek')]

        if request.method == 'POST':
            print("\n=== OTRZYMANO POST ===")
            print("\nWSZYSTKIE DANE FORMULARZA:")
            for key, value in request.form.items():
                print(f"{key}: {value}")

            if form.validate():
                print("\n=== FORMULARZ PRZESZEDŁ WALIDACJĘ ===")
                try:
                    query = Query(
                        name=form.name.data,
                        market=form.market.data,
                        client=form.client.data,
                        investment=form.investment.data,
                        preferred_date=form.preferred_date.data,
                        query_comments=form.comments.data
                    )

                    db.session.add(query)
                    db.session.flush()

                    print("\n=== PRZETWARZANIE KABLI ===")
                    print(f"Liczba kabli do przetworzenia: {len(form.cables)}")

                    for i, cable_form in enumerate(form.cables):
                        print(f"\nPrzetwarzanie kabla {i+1}:")

                        voltage_value = None
                        for field_name, value in request.form.items():
                            if field_name.startswith(f'voltage-{i}'):
                                if value != 'other':
                                    voltage_value = value
                                break

                        cable = Cable(
                            query_id=query.id,
                            cable_type=cable_form.cable_type.data,
                            voltage=voltage_value,
                            length=cable_form.length.data,
                            packaging=cable_form.packaging.data,
                            specific_lengths=cable_form.specific_lengths.data if cable_form.packaging.data == 'dokładne odcinki' else None,
                            comments=cable_form.comments.data
                        )
                        db.session.add(cable)
                        print(f"Kabel {i+1} dodany do sesji")

                    db.session.commit()
                    print("Zmiany zapisane")

                    send_new_query_notification(query)
                    flash('Zapytanie zostało pomyślnie dodane!', 'success')
                    return redirect(url_for('index'))

                except Exception as e:
                    print(f"\n!!! BŁĄD PODCZAS ZAPISYWANIA: {str(e)}")
                    print(f"Traceback:\n{traceback.format_exc()}")
                    db.session.rollback()
                    raise
            else:
                print("\n!!! BŁĘDY WALIDACJI:")
                print(form.errors)
                for field, errors in form.errors.items():
                    for error in errors:
                        flash(f'Błąd w polu {field}: {error}', 'danger')

        return render_template('new_query.html',
                             form=form,
                             markets=markets,
                             salespersons_by_market=json.dumps(salespersons_by_market))

    except Exception as e:
        print(f"\n!!! BŁĄD GŁÓWNY: {str(e)}")
        print(f"Traceback:\n{traceback.format_exc()}")
        flash('Wystąpił błąd podczas dodawania zapytania.', 'error')
        return redirect(url_for('index'))

@app.route('/response/<int:query_id>', methods=['GET', 'POST'])
@login_required
def respond(query_id):
    if not session.get('is_admin'):
        flash('Brak uprawnień do odpowiadania na zapytania.', 'danger')
        return redirect(url_for('index'))

    try:
        query = Query.query.get_or_404(query_id)
        form = ResponseForm()

        if request.method == 'POST':
            print("Otrzymano POST request")
            unanswered_cables = [cable for cable in query.cables if not cable.response]

            # Przygotowanie formularzy z zachowanymi danymi
            cable_response_forms = []
            has_errors = False

            for i, cable in enumerate(unanswered_cables):
                # Tworzenie formularza dla każdego kabla
                response_form = CableResponseForm()

                # Zachowanie wszystkich wprowadzonych wartości
                form_data = {
                    'price_per_meter_client': request.form.get(f'cable_responses-{i}-price_per_meter_client', ''),
                    'price_per_meter_purchase': request.form.get(f'cable_responses-{i}-price_per_meter_purchase', ''),
                    'delivery_option': request.form.get(f'cable_responses-{i}-delivery_option', ''),
                    'validity_option': request.form.get(f'cable_responses-{i}-validity_option', ''),
                    'manufacturer': request.form.get(f'cable_responses-{i}-manufacturer', ''),
                    'comments': request.form.get(f'cable_responses-{i}-comments', ''),
                    'delivery_date': request.form.get(f'cable_responses-{i}-delivery_date', '')
                }

                # Sprawdzanie błędów walidacji
                if not form_data['price_per_meter_client'] or not form_data['price_per_meter_purchase']:
                    has_errors = True
                    flash(f'Musisz podać obie ceny dla kabla {i+1}.', 'danger')
                else:
                    try:
                        price_client = float(form_data['price_per_meter_client'])
                        price_purchase = float(form_data['price_per_meter_purchase'])
                        if price_client <= 0 or price_purchase <= 0:
                            has_errors = True
                            flash(f'Ceny dla kabla {i+1} muszą być większe od 0.', 'danger')
                    except ValueError:
                        has_errors = True
                        flash(f'Nieprawidłowy format ceny dla kabla {i+1}.', 'danger')

                if not form_data['delivery_option']:
                    has_errors = True
                    flash(f'Wybierz termin dostawy dla kabla {i+1}.', 'danger')
                elif form_data['delivery_option'] == 'custom' and not form_data['delivery_date']:
                    has_errors = True
                    flash(f'Wybierz datę dostawy dla kabla {i+1}.', 'danger')

                if not form_data['validity_option']:
                    has_errors = True
                    flash(f'Wybierz ważność oferty dla kabla {i+1}.', 'danger')

                # Przypisanie zachowanych wartości do formularza
                for key, value in form_data.items():
                    if hasattr(response_form, key):
                        setattr(response_form, key, value)

                cable_response_forms.append(response_form)

            if has_errors:
                return render_template(
                    'response.html',
                    form=form,
                    query=query,
                    cable_data=zip(unanswered_cables, cable_response_forms),
                    cable_response_form=CableResponseForm(),
                    saved_values=cable_forms  # Przekazujemy zachowane wartości

                )

            try:
                new_responses = []
                for i, cable in enumerate(unanswered_cables):
                    delivery_option = request.form.get(f'cable_responses-{i}-delivery_option')
                    if delivery_option == 'custom':
                        delivery_start = datetime.strptime(
                            request.form.get(f'cable_responses-{i}-delivery_date'),
                            '%Y-%m-%d'
                        ).date()
                        delivery_end = delivery_start
                    else:
                        delivery_start, delivery_end = calculate_delivery_dates(delivery_option)

                    validity_date = calculate_validity_date(
                        request.form.get(f'cable_responses-{i}-validity_option')
                    )

                    comments = request.form.get(f'cable_responses-{i}-comments', '')
                    if delivery_option == 'zielonka':
                        comments = f"Dostępne w Zielonce. {comments}"
                    elif delivery_option == 'bialystok':
                        comments = f"Dostępne w Białymstoku. {comments}"
                    elif delivery_option == 'depozyt':
                        comments = f"Depozyt. {comments}"

                    response = CableResponse(
                        cable_id=cable.id,
                        price_per_meter_client=float(request.form.get(f'cable_responses-{i}-price_per_meter_client')),
                        price_per_meter_purchase=float(request.form.get(f'cable_responses-{i}-price_per_meter_purchase')),
                        manufacturer=request.form.get(f'cable_responses-{i}-manufacturer'),
                        delivery_date_start=delivery_start,
                        delivery_date_end=delivery_end,
                        validity_date=validity_date,
                        comments=comments.strip()
                    )
                    db.session.add(response)
                    new_responses.append(response)

                db.session.commit()
                send_response_notification(query, list(zip(unanswered_cables, new_responses)))
                flash('Odpowiedzi zostały pomyślnie dodane!', 'success')
                return redirect(url_for('index'))

            except Exception as e:
                db.session.rollback()
                print(f"Błąd podczas zapisywania odpowiedzi: {str(e)}")
                flash('Wystąpił błąd podczas zapisywania odpowiedzi.', 'danger')
                return render_template(
                    'response.html',
                    form=form,
                    query=query,
                    cable_data=zip(unanswered_cables, cable_response_forms),
                    cable_response_form=CableResponseForm(),
                    saved_values=None
                )

        # Dla metody GET
        unanswered_cables = [cable for cable in query.cables if not cable.response]
        form.cable_responses = [CableResponseForm() for _ in unanswered_cables]

        return render_template(
            'response.html',
            form=form,
            query=query,
            cable_data=zip(unanswered_cables, form.cable_responses),
            cable_response_form=CableResponseForm()
        )

    except Exception as e:
        print(f"Błąd w respond(): {str(e)}")
        flash('Wystąpił błąd podczas przetwarzania zapytania.', 'error')
        return redirect(url_for('index'))


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
        query_time = query.date_submitted.replace(tzinfo=ZoneInfo("Europe/Warsaw"))
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
            app.logger.info(f"Sent reminder email for query {query.id} after {int(hours_difference)} hours")
    except Exception as e:
        app.logger.error(f"Error sending reminder email: {str(e)}")

def send_response_notification(query, responses):
    print("\n=== Rozpoczęcie wysyłania powiadomień ===")
    try:
        salesperson_email = email_mapping.get(query.name)
        print(f"Handlowiec: {query.name}")
        print(f"Email handlowca: {salesperson_email}")
        print(f"Klient: {query.client}")

        for cable, response in responses:
            print(f"Kabel: {cable.cable_type}")
            print(f"Cena klienta: {response.price_per_meter_client}")
            print(f"Cena zakupu: {response.price_per_meter_purchase}")

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

@app.route('/archive')
@app.route('/archive/<timeframe>')
@login_required
def archive(timeframe='week'):
    try:
        comment_form = CommentForm()
        delete_form = DeleteForm()

        # Obliczanie dat granicznych
        current_time = datetime.now(ZoneInfo("Europe/Warsaw"))
        week_ago = current_time - timedelta(days=7)
        two_weeks_ago = current_time - timedelta(days=14)
        month_ago = current_time - timedelta(days=31)

        # Podstawowe zapytanie z eager loading wszystkich potrzebnych relacji
        base_query = Query.query\
            .options(
                db.joinedload(Query.cables).joinedload(Cable.response),
                db.joinedload(Query.comments)
            )

        # Filtrowanie po dacie
        if timeframe == 'week':
            base_query = base_query.filter(
                Query.date_submitted <= week_ago,
                Query.date_submitted > two_weeks_ago
            )
        elif timeframe == 'month':
            base_query = base_query.filter(
                Query.date_submitted <= week_ago,
                Query.date_submitted > month_ago
            )
        else:  # 'all'
            base_query = base_query.filter(Query.date_submitted <= week_ago)

        # Pobieranie filtrów z URL
        name_filter = request.args.get('name')
        market_filter = request.args.get('market')
        client_filter = request.args.get('client')
        cable_filter = request.args.get('cable_type')
        is_won_filter = request.args.get('is_won')

        # Aplikowanie filtrów
        if name_filter:
            base_query = base_query.filter(Query.name == name_filter)
        if market_filter:
            base_query = base_query.filter(Query.market == market_filter)
        if client_filter:
            base_query = base_query.filter(Query.client.ilike(f"%{client_filter}%"))
        if is_won_filter in ['true', 'false']:
            is_won = is_won_filter == 'true'
            base_query = base_query.filter(Query.is_won == is_won)
        if cable_filter:
            pat = f"%{cable_filter.strip()}%"
            base_query = base_query.filter(
                Query.cables.any(Cable.cable_type.ilike(pat))
            )

        # Wykonanie zapytania i sortowanie
        queries = base_query.order_by(Query.date_submitted.desc()).all()

        # Przygotowanie danych
        query_data = []
        for query in queries:
            try:
                cables_info = []
                for cable in query.cables:
                    cable_info = {
                        'type': cable.cable_type,
                        'length': cable.length,
                        'voltage': cable.voltage,
                        'packaging': cable.packaging,
                        'specific_lengths': cable.specific_lengths,
                        'comments': cable.comments,
                    }

                    # Sprawdzanie odpowiedzi
                    if cable.response:
                        cable_info['response'] = {
                            'price_per_meter_client': cable.response.price_per_meter_client,
                            'price_per_meter_purchase': cable.response.price_per_meter_purchase,
                            'manufacturer': cable.response.manufacturer,
                            'delivery_date_start': cable.response.delivery_date_start,
                            'delivery_date_end': cable.response.delivery_date_end,
                            'validity_date': cable.response.validity_date,
                            'comments': cable.response.comments or '',
                            'date_responded': cable.response.date_responded
                        }
                    else:
                        cable_info['response'] = None

                    cables_info.append(cable_info)

                # Liczenie nieprzeczytanych komentarzy
                unread_comments_count = sum(1 for comment in query.comments if not comment.is_read)

                query_data.append({
                    'query': query,
                    'cables': cables_info,
                    'is_responded': all(cable.response is not None for cable in query.cables),
                    'unread_comments_count': unread_comments_count
                })

            except Exception as cable_error:
                # Pominięcie problematycznego zapytania zamiast przerywania całego procesu
                app.logger.error(f"Błąd podczas przetwarzania zapytania: {cable_error}")
                continue

        # Pobieranie unikalnych wartości dla filtrów
        all_markets = sorted(set(q.market for q in Query.query.all()))
        all_names = sorted(set(q.name for q in Query.query.all()))

        return render_template('archive.html',
                             query_data=query_data,
                             delete_form=delete_form,
                             comment_form=comment_form,
                             current_timeframe=timeframe,
                             filters={
                                 'name': name_filter,
                                 'market': market_filter,
                                 'client': client_filter,
                                 'cable_type': cable_filter,
                                 'is_won': is_won_filter
                             },
                             all_markets=all_markets,
                             all_names=all_names)

    except Exception as e:
        app.logger.error(f"Błąd w archive(): {e}")
        flash('Wystąpił błąd podczas ładowania archiwum.', 'error')
        return redirect(url_for('index'))

@app.route('/delete_query/<int:query_id>', methods=['POST'])
@login_required
def delete_query(query_id):
    print(f"Próba usunięcia zapytania {query_id}")  # Dodaj to logowanie
    if not session.get('can_delete'):
        flash('Brak uprawnień do usuwania zapytań.', 'danger')
        return redirect(url_for('index'))

    try:
        # Najpierw sprawdźmy, czy zapytanie istnieje
        query = Query.query.get_or_404(query_id)

        print(f"\n=== Rozpoczynam proces usuwania zapytania ID: {query_id} ===")
        print(f"Klient: {query.client}")
        print(f"Liczba kabli: {len(query.cables)}")

        # Rozpocznij transakcję
        db.session.begin_nested()

        # Usuwanie odpowiedzi i kabli
        for cable in query.cables:
            if cable.response:
                print(f"Usuwam odpowiedź dla kabla ID: {cable.id}")
                db.session.delete(cable.response)
            print(f"Usuwam kabel ID: {cable.id}")
            db.session.delete(cable)

        # Usuwanie samego zapytania
        print(f"Usuwam zapytanie ID: {query_id}")
        db.session.delete(query)

        # Zatwierdź zmiany
        db.session.commit()
        print("=== Usuwanie zakończone sukcesem ===\n")

        flash('Zapytanie zostało pomyślnie usunięte.', 'success')

    except Exception as e:
        print(f"!!! BŁĄD podczas usuwania: {str(e)}")
        print(f"Traceback:\n{traceback.format_exc()}")
        db.session.rollback()
        flash(f'Wystąpił błąd podczas usuwania zapytania: {str(e)}', 'error')

    return redirect(url_for('index'))

@app.route('/get-salespersons/<market>')
@login_required
def get_salespersons(market):
    try:
        _, salespersons_by_market, _ = load_data_from_excel()
        return jsonify(salespersons_by_market.get(market, []))
    except Exception as e:
        app.logger.error(f"Error getting salespersons: {str(e)}")
        return jsonify([])

@app.context_processor
def utility_processor():
    def format_datetime(dt):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local_dt = dt.astimezone(ZoneInfo("Europe/Warsaw"))
        return (local_dt - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')

    return {
        'format_datetime': format_datetime,
        'datetime': datetime
    }

@app.route('/add-comment', methods=['POST'])
def add_comment():
    form = CommentForm()
    if form.validate_on_submit():
        # Pobierz dane z formularza
        query_id = request.form.get('query_id')
        response_id = request.form.get('response_id')
        new_comment = Comment(
            content=form.content.data,
            query_id=query_id if query_id else None,
            author=session.get('username')  # Zakładam, że użytkownik jest zalogowany
        )
        db.session.add(new_comment)
        db.session.commit()
        flash('Komentarz został dodany!', 'success')
    else:
        flash('Nie udało się dodać komentarza.', 'danger')
    return redirect(request.referrer)



@app.route('/edit-query/<int:query_id>', methods=['GET', 'POST'])
@login_required
def edit_query(query_id):
    query = Query.query.get_or_404(query_id)

    # Sprawdź, czy zapytanie można edytować
    if query.is_all_responded():
        flash('Nie można edytować zapytania, na które udzielono już odpowiedzi.', 'danger')
        return redirect(url_for('index'))

    # Sprawdź, czy użytkownik jest właścicielem zapytania
    if query.name != session.get('username'):
        flash('Nie masz uprawnień do edycji tego zapytania.', 'danger')
        return redirect(url_for('index'))

    # Przygotuj dane dla formularza
    markets, salespersons_by_market, _ = load_data_from_excel()
    form = QueryForm()

    # Ustaw opcje wyboru dla pól market i name
    form.market.choices = [('', 'Wybierz rynek')] + [(market, market) for market in markets]

    if request.method == 'GET':
        # Wypełnij formularz danymi z istniejącego zapytania
        form.market.data = query.market
        form.name.data = query.name
        form.client.data = query.client
        form.investment.data = query.investment
        form.preferred_date.data = query.preferred_date
        form.comments.data = query.query_comments  # Zmienione z query.comments na query.query_comments

        # Upewnij się, że mamy wystarczającą liczbę formularzy dla kabli
        while len(form.cables) < len(query.cables):
            form.cables.append_entry()

        # Wypełnij dane kabli
        for i, cable in enumerate(query.cables):
            form.cables[i].cable_type.data = cable.cable_type
            form.cables[i].length.data = cable.length
            form.cables[i].packaging.data = cable.packaging
            form.cables[i].specific_lengths.data = cable.specific_lengths
            form.cables[i].comments.data = cable.comments

    if request.method == 'POST':
        # Ustaw choices dla name przy POST
        if form.market.data:
            form.name.choices = [(name, name) for name in salespersons_by_market.get(form.market.data, [])]
        else:
            form.name.choices = [(query.name, query.name)]  # Zachowaj obecnego handlowca jako opcję

        if form.validate():
            try:
                # Aktualizuj dane zapytania
                query.client = form.client.data
                query.investment = form.investment.data
                query.preferred_date = form.preferred_date.data
                query.query_comments = form.comments.data  # Zmienione z comments na query_comments

                # Usuń stare kable
                for cable in query.cables:
                    db.session.delete(cable)

                # Dodaj nowe kable
                for idx, cable_form in enumerate(form.cables):  # Dodajemy enumerate aby mieć indeks
                    voltage_value = None
                    # Sprawdź przyciski napięcia
                    for field_name, value in request.form.items():
                        if field_name.startswith(f'voltage-{i}'):
                            if value != 'other':
                                voltage_value = value
                            break

                    cable = Cable(
                        query_id=query.id,
                        cable_type=cable_form.cable_type.data,
                        voltage=voltage_value,
                        length=cable_form.length.data,
                        packaging=cable_form.packaging.data,
                        specific_lengths=cable_form.specific_lengths.data if cable_form.packaging.data == 'dokładne odcinki' else None,
                        comments=cable_form.comments.data
                    )
                    db.session.add(cable)

                db.session.commit()
                flash('Zapytanie zostało zaktualizowane.', 'success')
                return redirect(url_for('index'))

            except Exception as e:
                print(f"Błąd podczas aktualizacji: {str(e)}")
                db.session.rollback()
                flash(f'Wystąpił błąd podczas aktualizacji zapytania: {str(e)}', 'danger')

    # Aktualizuj choices dla name w przypadku GET lub błędu walidacji
    if query.market:
        form.name.choices = [(name, name) for name in salespersons_by_market.get(query.market, [])]
    else:
        form.name.choices = [(query.name, query.name)]

    return render_template('edit_query.html',
                         form=form,
                         query=query,
                         markets=markets,
                         salespersons_by_market=json.dumps(salespersons_by_market))

@app.route('/update_sale_status/<int:query_id>', methods=['POST'])
@login_required
def update_sale_status(query_id):
    try:
        query = Query.query.get_or_404(query_id)

        # Sprawdź czy zalogowany użytkownik jest autorem zapytania
        if session.get('username') != query.name:
            return jsonify({'status': 'error', 'message': 'Brak uprawnień'}), 403

        data = request.get_json()
        new_status = data.get('is_won')

        query.is_won = new_status
        db.session.commit()

        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Błąd podczas aktualizacji statusu: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/mark-comments-read/<int:query_id>', methods=['POST'])
@login_required
def mark_comments_read(query_id):
    try:
        # Oznacz komentarze jako przeczytane dopiero po kliknięciu przycisku
        if request.json and request.json.get('mark_as_read'):
            query = Query.query.get_or_404(query_id)
            for comment in query.comments:
                if not comment.is_read:
                    comment.is_read = True
            db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/toggle-comments-read/<int:query_id>', methods=['POST'])
@login_required
def toggle_comments_read(query_id):
    try:
        query = Query.query.get_or_404(query_id)
        is_read = request.json.get('is_read', True)

        # Aktualizuj status komentarzy
        for comment in query.comments:
            comment.is_read = is_read

        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/instruction')
def instruction():
    return render_template('instruction.html')

# Dodaj obsługę błędu 401 (Unauthorized)
@app.errorhandler(401)
def unauthorized(error):
    flash('Musisz się zalogować, aby uzyskać dostęp do tej strony.', 'warning')
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)