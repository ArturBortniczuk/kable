from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from forms import LoginForm
from config import config
import pandas as pd
from utils import generate_password

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    if session.get('logged_in'):
        return redirect(url_for('main.index'))

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
                return redirect(next_url or url_for('main.index'))

            if form.username.data == 'superadmin' and form.password.data == 'super123':
                session['logged_in'] = True
                session['username'] = 'SuperAdmin'
                session['is_admin'] = True
                session['can_delete'] = True
                flash('Zalogowano pomyślnie!', 'success')
                next_url = session.pop('next_url', None)
                return redirect(next_url or url_for('main.index'))

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
                    session['market'] = row[1]  
                    flash('Zalogowano pomyślnie!', 'success')

                    next_url = session.pop('next_url', None)
                    return redirect(next_url or url_for('main.index'))

            flash('Nieprawidłowy email lub hasło.', 'danger')

        except Exception as e:
            print(f"Błąd podczas logowania: {str(e)}")
            flash('Wystąpił błąd podczas logowania.', 'danger')

    return render_template('login.html', form=form)

@auth_bp.route('/logout', endpoint='logout')
def logout():
    session.clear()
    flash('Wylogowano pomyślnie!', 'success')
    return redirect(url_for('auth.login'))
