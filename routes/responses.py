from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from forms import ResponseForm, CableResponseForm
from models import Query, CableResponse
from extensions import db
from utils import login_required, calculate_delivery_dates, calculate_validity_date, send_response_notification
from datetime import datetime

responses_bp = Blueprint('responses', __name__)

@responses_bp.route('/response/<int:query_id>', methods=['GET', 'POST'], endpoint='respond')
@login_required
def respond(query_id):
    if not session.get('is_admin'):
        flash('Brak uprawnień do odpowiadania na zapytania.', 'danger')
        return redirect(url_for('main.index'))

    try:
        query = Query.query.get_or_404(query_id)
        form = ResponseForm()

        if request.method == 'POST':
            print("Otrzymano POST request")
            unanswered_cables = [cable for cable in query.cables if not cable.response]

            # Przygotowanie formularzy z zachowanymi danymi
            cable_response_forms = []
            has_errors = False

            # Because we re-construct forms manually or via loop, we need logic.
            # In original code:
            for i, cable in enumerate(unanswered_cables):
                response_form = CableResponseForm()
                
                form_data = {
                    'price_per_meter_client': request.form.get(f'cable_responses-{i}-price_per_meter_client', ''),
                    'price_per_meter_purchase': request.form.get(f'cable_responses-{i}-price_per_meter_purchase', ''),
                    'delivery_option': request.form.get(f'cable_responses-{i}-delivery_option', ''),
                    'validity_option': request.form.get(f'cable_responses-{i}-validity_option', ''),
                    'manufacturer': request.form.get(f'cable_responses-{i}-manufacturer', ''),
                    'comments': request.form.get(f'cable_responses-{i}-comments', ''),
                    'delivery_date': request.form.get(f'cable_responses-{i}-delivery_date', '')
                }

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
                    saved_values=cable_response_forms # In original code was cable_forms but cable_response_forms seems correct here based on context
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
                return redirect(url_for('main.index'))

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
        return redirect(url_for('main.index'))
