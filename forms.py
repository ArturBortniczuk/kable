from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, DateField, TextAreaField, FloatField, FieldList, FormField, PasswordField, BooleanField
from wtforms.validators import DataRequired, NumberRange, Length, Optional, ValidationError
from datetime import datetime
from flask import request


class UserForm(FlaskForm):
    username = StringField('Nazwa użytkownika', validators=[DataRequired()])
    email = StringField('Email')
    password = PasswordField('Hasło')
    market = StringField('Rynek')
    is_admin = BooleanField('Administrator')
    can_delete = BooleanField('Może usuwać')  # Dodaj ten import na początku pliku


class CableForm(FlaskForm):
    class Meta:
        csrf = False

    cable_type = StringField('Rodzaj kabla',
                           validators=[DataRequired(message="To pole jest wymagane")],
                           render_kw={'class': 'form-control cable-type-input'})

    length = IntegerField('Długość w metrach',
                         validators=[DataRequired(message="To pole jest wymagane"),
                                   NumberRange(min=1, message="Długość musi być większa niż 0")],
                         render_kw={'type': 'number', 'min': '1'})

    packaging = SelectField('Konfekcja',
                          choices=[('pełne bębny', 'Pełne bębny'),
                                  ('dokładne odcinki', 'Dokładne odcinki')],
                          validators=[DataRequired(message="Wybierz rodzaj konfekcji")],
                          default='pełne bębny')

    specific_lengths = TextAreaField('Dokładne odcinki',
                                   validators=[Optional()],
                                   render_kw={
                                       'rows': '2',
                                       'readonly': True,  # To pole będzie wypełniane automatycznie
                                       'placeholder': 'To pole wypełni się automatycznie na podstawie wprowadzonych odcinków'
                                   })

    comments = TextAreaField('Uwagi',
                           validators=[Optional()],
                           render_kw={'rows': '2',
                                    'placeholder': 'Przy wyborze opcji "inne" dla napięcia, wpisz tutaj wartość napięcia'})

    def validate_form(self):  # Zmień nazwę z validate na validate_form
        if not super().validate():
            return False

        if self.cable_type.data:
            cable_type = self.cable_type.data.upper()
            voltage_field_name = None

            for field_name in request.form:
                if field_name.startswith('voltage-') and 'other' in request.form[field_name]:
                    voltage_field_name = field_name
                    break

            if ('XRU' in cable_type or 'XNRU' in cable_type) and voltage_field_name and not self.comments.data:
                self.comments.errors.append('Przy wyborze opcji "inne" dla napięcia, należy podać wartość w uwagach')
                return False

        return True


class QueryForm(FlaskForm):
    name = SelectField('Imię i nazwisko',
                      validators=[Optional()])  # Zmienione z DataRequired na Optional

    market = SelectField('Rynek',
                      validators=[Optional()])  # Zmienione z DataRequired na Optional

    client = StringField('Klient',
                        validators=[DataRequired(message="To pole jest wymagane"),
                                  Length(min=2, max=100, message="Nazwa klienta musi mieć od 2 do 100 znaków")])

    investment = StringField('Inwestycja',
                            validators=[Optional(),
                            Length(max=200, message="Nazwa inwestycji nie może przekraczać 200 znaków")])

    cables = FieldList(FormField(CableForm), min_entries=1)

    preferred_date = DateField('Preferowana data dostawy',
                             format='%Y-%m-%d',
                             validators=[DataRequired(message="Wybierz datę")],
                             render_kw={'type': 'date', 'min': datetime.now().strftime('%Y-%m-%d')})

    comments = TextAreaField('Uwagi',
                           validators=[Optional(),
                                     Length(max=500, message="Uwagi nie mogą przekraczać 500 znaków")])

    def validate_preferred_date(self, field):
        if field.data < datetime.now().date():
            raise ValidationError('Data dostawy nie może być z przeszłości')

    def validate(self):
        print("\n=== DEBUGOWANIE WALIDACJI QUERYFORM ===")

        # Najpierw sprawdzamy podstawową walidację
        if not super().validate():
            print("Błąd podstawowej walidacji")
            return False

        # Sprawdzamy walidację każdego kabla
        print("\nSprawdzanie formularzy kabli:")
        for i, cable_form in enumerate(self.cables):
            print(f"\nKabel {i+1}:")
            print(f"cable_type: {cable_form.cable_type.data}")
            print(f"length: {cable_form.length.data}")
            print(f"packaging: {cable_form.packaging.data}")

            # Ważne: używamy validate_form zamiast validate
            if not cable_form.validate_form():
                print(f"Błąd walidacji kabla {i+1}")
                return False

        return True

class LoginForm(FlaskForm):
    username = StringField('Nazwa użytkownika',
                         validators=[DataRequired(message="Wprowadź nazwę użytkownika")])
    password = StringField('Hasło',
                         validators=[DataRequired(message="Wprowadź hasło")])

class CableResponseForm(FlaskForm):
    class Meta:
        csrf = False

    price_per_meter_client = FloatField('Cena dla klienta',
                                validators=[DataRequired(message="Cena dla klienta jest wymagana"),
                                          NumberRange(min=0.01, message="Cena musi być większa niż 0")],
                                render_kw={'type': 'number', 'step': '0.01'})

    price_per_meter_purchase = FloatField('Cena zakupu',
                                validators=[DataRequired(message="Cena zakupu jest wymagana"),
                                          NumberRange(min=0.01, message="Cena musi być większa niż 0")],
                                render_kw={'type': 'number', 'step': '0.01'})

    delivery_option = StringField('Termin dostawy',
                              validators=[DataRequired(message="Wybierz termin dostawy")])

    delivery_date = DateField('Data dostawy',
                              format='%Y-%m-%d',
                              validators=[Optional()],
                              render_kw={'type': 'date', 'min': datetime.now().strftime('%Y-%m-%d')})

    validity_option = StringField('Ważność oferty',
                              validators=[DataRequired(message="Wybierz okres ważności oferty")])

    comments = TextAreaField('Uwagi',
                           validators=[Optional(),
                                     Length(max=500, message="Uwagi nie mogą przekraczać 500 znaków")])

    def validate(self):
        if not super().validate():
            return False

        if not self.price_per_meter_client.data and not self.price_per_meter_purchase.data:
            self.price_per_meter_client.errors.append('Musisz podać przynajmniej jedną cenę')
            return False

        return True

class ResponseForm(FlaskForm):
    cable_responses = FieldList(FormField(CableResponseForm), min_entries=0)

    def validate(self):
        if not super().validate():
            return False

        print("Starting ResponseForm validation")

        if len(self.cable_responses) == 0:
            print("No cable responses found")
            return False

        # Sprawdzamy czy mamy dane w formularzu
        if not request.form:
            print("No form data")
            return False

        try:
            # Pobierz wszystkie dane z formularza
            form_data = {}
            for key in request.form:
                if key.startswith('cable_responses-'):
                    form_data[key] = request.form[key]

            # Sprawdź czy mamy odpowiedzi dla kabli
            response_count = len([key for key in form_data if key.endswith('-price_per_meter_client')])
            print(f"Found {response_count} responses")

            if response_count == 0:
                return False

            # Sprawdź każdą odpowiedź
            for i in range(response_count):
                price_client = form_data.get(f'cable_responses-{i}-price_per_meter_client')
                price_purchase = form_data.get(f'cable_responses-{i}-price_per_meter_purchase')
                delivery_option = form_data.get(f'cable_responses-{i}-delivery_option')
                validity_option = form_data.get(f'cable_responses-{i}-validity_option')

                # Sprawdź czy mamy wszystkie wymagane pola
                if not all([price_client, price_purchase, delivery_option, validity_option]):
                    return False

                # Sprawdź poprawność cen
                try:
                    float_price_client = float(price_client)
                    float_price_purchase = float(price_purchase)
                    if float_price_client <= 0 or float_price_purchase <= 0:
                        return False
                except (ValueError, TypeError):
                    return False

            return True

        except Exception as e:
            print(f"Validation error: {e}")
            return False

class DeleteForm(FlaskForm):
    """Empty form for CSRF protection"""
    pass

class CommentForm(FlaskForm):
    content = TextAreaField(
        'Komentarz',
        validators=[
            DataRequired(message="Komentarz nie może być pusty"),
            Length(max=500, message="Komentarz nie może przekraczać 500 znaków")
        ]
    )
