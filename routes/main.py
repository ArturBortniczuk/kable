from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from forms import DeleteForm, CommentForm
from extensions import db
from models import Query, Cable, Comment
from utils import login_required
import traceback

main_bp = Blueprint('main', __name__)

@main_bp.route('/', endpoint='index')
def index():
    comment_form = CommentForm()
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))

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


@main_bp.route('/archive', endpoint='archive')
@main_bp.route('/archive/<timeframe>', endpoint='archive')
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
                current_app.logger.error(f"Błąd podczas przetwarzania zapytania: {cable_error}")
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
        current_app.logger.error(f"Błąd w archive(): {e}")
        flash('Wystąpił błąd podczas ładowania archiwum.', 'error')
        return redirect(url_for('main.index'))

@main_bp.route('/instruction', endpoint='instruction')
def instruction():
    return render_template('instruction.html')
