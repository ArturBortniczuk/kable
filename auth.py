from functools import wraps
from flask import session, flash, redirect, url_for

# Lista uprawnionych użytkowników
AUTHORIZED_USERS = {
    'admin': {
        'password': 'admin123',  # W produkcji użyj zahashowanego hasła
        'role': 'pricing_admin'
    }
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Proszę się zalogować.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def pricing_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or session.get('user_role') != 'pricing_admin':
            flash('Brak uprawnień do wykonania tej operacji.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function