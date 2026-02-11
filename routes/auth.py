from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from forms import LoginForm
from config import config
from models import User
from utils import generate_password

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    if session.get('logged_in'):
        return redirect(url_for('main.index'))

    form = LoginForm()
    if request.method == 'POST' and form.validate():
        try:
            user = User.query.filter_by(username=form.username.data).first()
            
            # Próba logowania po emailu, jeśli nie znaleziono po nazwie
            if not user:
                user = User.query.filter_by(email=form.username.data).first()

            if user and user.check_password(form.password.data):
                # Zalogowano pomyślnie
                session['logged_in'] = True
                session['user_id'] = user.id
                session['username'] = user.username
                session['email'] = user.email
                session['is_admin'] = user.is_admin
                session['can_delete'] = user.can_delete
                session['market'] = user.market
                
                flash(f'Witaj, {user.username}!', 'success')
                
                next_url = session.pop('next_url', None)
                return redirect(next_url or url_for('main.index'))
            else:
                flash('Nieprawidłowa nazwa użytkownika lub hasło.', 'danger')

        except Exception as e:
            print(f"Błąd podczas logowania: {str(e)}")
            flash('Wystąpił błąd podczas logowania.', 'danger')

    return render_template('login.html', form=form)

@auth_bp.route('/logout', endpoint='logout')
def logout():
    session.clear()
    flash('Wylogowano pomyślnie!', 'success')
    return redirect(url_for('auth.login'))
