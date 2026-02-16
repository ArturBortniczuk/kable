from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, current_app
from forms import QueryForm
from models import Query, Cable
from extensions import db
from utils import login_required, load_data_from_excel, send_new_query_notification
import traceback
import json

queries_bp = Blueprint('queries', __name__)

def process_cable_form(cable_form, request_form, index, query_id):
    """
    Helper function to process cable form data and create a Cable object.
    Parameters:
        cable_form: The WTForm subform for the cable
        request_form: The raw request.form dictionary (for custom fields like voltage)
        index: The index of the cable in the form list
        query_id: The ID of the parent query
    """
    voltage_value = None
    voltage_key = f'voltage-{index}'
    
    if voltage_key in request_form:
        val = request_form[voltage_key]
        if val != 'other':
            voltage_value = val

    return Cable(
        query_id=query_id,
        cable_type=cable_form.cable_type.data,
        voltage=voltage_value,
        length=cable_form.length.data,
        packaging=cable_form.packaging.data,
        specific_lengths=cable_form.specific_lengths.data if cable_form.packaging.data == 'dokładne odcinki' else None,
        comments=cable_form.comments.data
    )

@queries_bp.route('/new-query', methods=['GET', 'POST'], endpoint='new_query')
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
                        
                        cable = process_cable_form(cable_form, request.form, i, query.id)
                        db.session.add(cable)
                        print(f"Kabel {i+1} dodany do sesji")

                    db.session.commit()
                    print("Zmiany zapisane")

                    send_new_query_notification(query)
                    flash('Zapytanie zostało pomyślnie dodane!', 'success')
                    return redirect(url_for('main.index'))

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
        return redirect(url_for('main.index'))

@queries_bp.route('/delete_query/<int:query_id>', methods=['POST'], endpoint='delete_query')
@login_required
def delete_query(query_id):
    print(f"Próba usunięcia zapytania {query_id}")
    if not session.get('can_delete'):
        flash('Brak uprawnień do usuwania zapytań.', 'danger')
        return redirect(url_for('main.index'))

    try:
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

    return redirect(url_for('main.index'))

@queries_bp.route('/get-salespersons/<market>', endpoint='get_salespersons')
@login_required
def get_salespersons(market):
    try:
        _, salespersons_by_market, _ = load_data_from_excel()
        return jsonify(salespersons_by_market.get(market, []))
    except Exception as e:
        current_app.logger.error(f"Error getting salespersons: {str(e)}")
        return jsonify([])

@queries_bp.route('/edit-query/<int:query_id>', methods=['GET', 'POST'], endpoint='edit_query')
@login_required
def edit_query(query_id):
    query = Query.query.get_or_404(query_id)

    # Sprawdź, czy zapytanie można edytować
    if query.is_all_responded():
        flash('Nie można edytować zapytania, na które udzielono już odpowiedzi.', 'danger')
        return redirect(url_for('main.index'))

    # Sprawdź, czy użytkownik jest właścicielem zapytania
    if query.name != session.get('username'):
        flash('Nie masz uprawnień do edycji tego zapytania.', 'danger')
        return redirect(url_for('main.index'))

    # Przygotuj dane dla formularza
    markets, salespersons_by_market, _ = load_data_from_excel()
    form = QueryForm()

    # Ustaw opcje wyboru dla pól market i name
    form.market.choices = [('', 'Wybierz rynek')] + [(market, market) for market in markets]

    if request.method == 'GET':
        form.market.data = query.market
        form.name.data = query.name
        form.client.data = query.client
        form.investment.data = query.investment
        form.preferred_date.data = query.preferred_date
        form.comments.data = query.query_comments

        while len(form.cables) < len(query.cables):
            form.cables.append_entry()

        for i, cable in enumerate(query.cables):
            form.cables[i].cable_type.data = cable.cable_type
            form.cables[i].length.data = cable.length
            form.cables[i].packaging.data = cable.packaging
            form.cables[i].specific_lengths.data = cable.specific_lengths
            form.cables[i].comments.data = cable.comments

    if request.method == 'POST':
        if form.market.data:
            form.name.choices = [(name, name) for name in salespersons_by_market.get(form.market.data, [])]
        else:
            form.name.choices = [(query.name, query.name)]

        if form.validate():
            try:
                query.client = form.client.data
                query.investment = form.investment.data
                query.preferred_date = form.preferred_date.data
                query.query_comments = form.comments.data

                for cable in query.cables:
                    db.session.delete(cable)

                for i, cable_form in enumerate(form.cables):
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

                db.session.commit()
                flash('Zapytanie zostało zaktualizowane.', 'success')
                return redirect(url_for('main.index'))

            except Exception as e:
                print(f"Błąd podczas aktualizacji: {str(e)}")
                db.session.rollback()
                flash(f'Wystąpił błąd podczas aktualizacji zapytania: {str(e)}', 'danger')

    if query.market:
        form.name.choices = [(name, name) for name in salespersons_by_market.get(query.market, [])]
    else:
        form.name.choices = [(query.name, query.name)]

    return render_template('edit_query.html',
                         form=form,
                         query=query,
                         markets=markets,
                         salespersons_by_market=json.dumps(salespersons_by_market))

@queries_bp.route('/update_sale_status/<int:query_id>', methods=['POST'], endpoint='update_sale_status')
@login_required
def update_sale_status(query_id):
    try:
        query = Query.query.get_or_404(query_id)

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
@queries_bp.route('/duplicate_query/<int:query_id>', methods=['POST'], endpoint='duplicate_query')
@login_required
def duplicate_query(query_id):
    try:
        original_query = Query.query.get_or_404(query_id)
        
        # Create new query with same details but current date
        new_query = Query(
            name=session.get('username'),  # Przypisz do aktualnego użytkownika
            market=original_query.market,
            client=original_query.client,
            investment=original_query.investment,
            preferred_date=original_query.preferred_date,
            query_comments=original_query.query_comments
        )
        
        db.session.add(new_query)
        db.session.flush()  # Get ID
        
        # Duplicate cables
        for original_cable in original_query.cables:
            new_cable = Cable(
                query_id=new_query.id,
                cable_type=original_cable.cable_type,
                voltage=original_cable.voltage,
                length=original_cable.length,
                packaging=original_cable.packaging,
                specific_lengths=original_cable.specific_lengths,
                comments=original_cable.comments
            )
            db.session.add(new_cable)
            
        db.session.commit()
        
        send_new_query_notification(new_query)
        flash('Zapytanie zostało zduplikowane.', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"Błąd podczas duplikowania: {str(e)}")
        flash('Wystąpił błąd podczas duplikowania zapytania.', 'danger')
        
    return redirect(url_for('main.index'))
