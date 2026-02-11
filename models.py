from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from extensions import db
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired

class Cable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query_id = db.Column(db.Integer, db.ForeignKey('query.id'), nullable=False)
    cable_type = db.Column(db.String(100), nullable=False)
    voltage = db.Column(db.String(20), nullable=True)
    length = db.Column(db.Integer, nullable=False)
    packaging = db.Column(db.String(50), nullable=False)
    specific_lengths = db.Column(db.Text, nullable=True)
    comments = db.Column(db.Text, nullable=True)
    response = db.relationship('CableResponse', backref='cable', uselist=False)

class Query(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    market = db.Column(db.String(50), nullable=False)
    client = db.Column(db.String(100), nullable=False)
    investment = db.Column(db.String(200), nullable=True)
    packaging = db.Column(db.String(50), nullable=True)
    preferred_date = db.Column(db.Date, nullable=False)
    query_comments = db.Column(db.Text, nullable=True)
    date_submitted = db.Column(db.DateTime, default=lambda: datetime.now(ZoneInfo("Europe/Warsaw")))
    cables = db.relationship('Cable', backref='query', lazy=True)
    is_won = db.Column(db.Boolean, default=None)
    comments = db.relationship('Comment', backref='query', lazy=True)


    def is_all_responded(self):
        if not self.cables:  # Jeśli nie ma kabli
            return False
        return all(cable.response is not None for cable in self.cables)

    def is_overdue(self):
        if self.is_all_responded():
            return False
            
        current_time = datetime.now(ZoneInfo("Europe/Warsaw"))
        query_time = self.date_submitted
        if query_time.tzinfo is None:
            query_time = query_time.replace(tzinfo=ZoneInfo("Europe/Warsaw"))
            
        # Oblicz czas, który upłynął (bez weekendów - opcjonalnie, na razie proste 48h)
        return (current_time - query_time) > timedelta(hours=48)

    def get_time_since_submission(self):
        """Oblicza czas od złożenia zapytania lub czas reakcji jeśli odpowiedziano."""
        current_time = datetime.now(ZoneInfo("Europe/Warsaw"))
        query_time = self.date_submitted
        
        if query_time.tzinfo is None:
            query_time = query_time.replace(tzinfo=ZoneInfo("Europe/Warsaw"))

        if self.is_all_responded():
            # Znajdź najnowszą odpowiedź
            last_response_date = None
            for cable in self.cables:
                if cable.response:
                    resp_date = cable.response.date_responded
                    if resp_date.tzinfo is None:
                        resp_date = resp_date.replace(tzinfo=ZoneInfo("Europe/Warsaw"))
                    
                    if last_response_date is None or resp_date > last_response_date:
                        last_response_date = resp_date
            
            if last_response_date:
                time_diff = last_response_date - query_time
            else:
                time_diff = current_time - query_time
        else:
            time_diff = current_time - query_time

        hours = int(time_diff.total_seconds() // 3600)
        minutes = int((time_diff.total_seconds() % 3600) // 60)
        seconds = int(time_diff.total_seconds() % 60)
        
        return {
            'hours': hours,
            'minutes': minutes,
            'seconds': seconds,
            'total_seconds': time_diff.total_seconds()
        }

    def get_unread_comments_count(self):
        """Zwraca liczbę nieprzeczytanych komentarzy."""
        return sum(1 for comment in self.comments if not comment.is_read)

class CableResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cable_id = db.Column(db.Integer, db.ForeignKey('cable.id'), nullable=False)
    price_per_meter_client = db.Column(db.Float, nullable=True)
    price_per_meter_purchase = db.Column(db.Float, nullable=True)
    manufacturer = db.Column(db.String(50), nullable=True)
    delivery_date_start = db.Column(db.Date, nullable=False)
    delivery_date_end = db.Column(db.Date, nullable=False)
    validity_date = db.Column(db.Date, nullable=False)
    comments = db.Column(db.Text, nullable=True)
    date_responded = db.Column(db.DateTime, default=lambda: datetime.now(ZoneInfo("Europe/Warsaw")))

    def validate(self):
        """Sprawdza, czy obie ceny są podane"""
        return self.price_per_meter_client is not None and self.price_per_meter_purchase is not None

class LoginForm(FlaskForm):
    username = StringField('Nazwa użytkownika', validators=[DataRequired()])
    password = PasswordField('Hasło', validators=[DataRequired()])

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(50), nullable=False)
    date_posted = db.Column(db.DateTime, default=lambda: datetime.now(ZoneInfo("Europe/Warsaw")))
    query_id = db.Column(db.Integer, db.ForeignKey('query.id'), nullable=False)
    is_read = db.Column(db.Boolean, default=False)  # Dodaj tę linię




