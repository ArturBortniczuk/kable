from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from models import User
from extensions import db
from utils import login_required
from forms import UserForm, DeleteForm
import traceback

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@login_required
def require_admin():
    if not session.get('is_admin'):
        flash('Brak dostępu. Wymagane uprawnienia administratora.', 'danger')
        return redirect(url_for('main.index'))

@admin_bp.route('/users', endpoint='users_list')
def users_list():
    users = User.query.order_by(User.username).all()
    return render_template('admin/users_list.html', users=users, delete_form=DeleteForm())

@admin_bp.route('/users/new', methods=['GET', 'POST'], endpoint='new_user')
def new_user():
    form = UserForm()
    if form.validate_on_submit():
        try:
            if User.query.filter_by(username=form.username.data).first():
                flash('Użytkownik o takiej nazwie już istnieje.', 'danger')
                return render_template('admin/user_form.html', form=form, title="Dodaj użytkownika")

            user = User(
                username=form.username.data,
                email=form.email.data,
                market=form.market.data,
                is_admin=form.is_admin.data,
                can_delete=form.can_delete.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Użytkownik został dodany.', 'success')
            return redirect(url_for('admin.users_list'))
        except Exception as e:
            db.session.rollback()
            print(f"Error adding user: {e}")
            flash('Błąd podczas dodawania użytkownika.', 'danger')

    return render_template('admin/user_form.html', form=form, title="Dodaj użytkownika")

@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'], endpoint='edit_user')
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    
    if request.method == 'GET':
        form.username.data = user.username
        form.email.data = user.email
        form.market.data = user.market
        form.is_admin.data = user.is_admin
        form.can_delete.data = user.can_delete

    if form.validate_on_submit():
        try:
            user.username = form.username.data
            user.email = form.email.data
            user.market = form.market.data
            user.is_admin = form.is_admin.data
            user.can_delete = form.can_delete.data
            
            if form.password.data:
                user.set_password(form.password.data)
                
            db.session.commit()
            flash('Użytkownik został zaktualizowany.', 'success')
            return redirect(url_for('admin.users_list'))
        except Exception as e:
            db.session.rollback()
            print(f"Error updating user: {e}")
            flash('Błąd podczas aktualizacji użytkownika.', 'danger')

    return render_template('admin/user_form.html', form=form, title="Edytuj użytkownika", user=user)

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'], endpoint='delete_user')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.username in ['Administrator', 'SuperAdmin']:
        flash('Nie można usunąć wbudowanych kont administratora.', 'danger')
        return redirect(url_for('admin.users_list'))
        
    try:
        db.session.delete(user)
        db.session.commit()
        flash('Użytkownik został usunięty.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting user: {e}")
        flash('Błąd podczas usuwania użytkownika.', 'danger')
        
    return redirect(url_for('admin.users_list'))

@admin_bp.route('/reports/weekly/send', methods=['GET'], endpoint='send_weekly_report')
def send_weekly_report():
    from services.reports import get_weekly_stats
    from flask_mail import Message
    from extensions import mail
    import traceback # Added import
    
    try:
        stats = get_weekly_stats()
        
        html_content = render_template(
            'emails/weekly_report.html',
            stats=stats,
            app_url=request.host_url.rstrip('/')
        )
        
        msg = Message(
            subject=f'Raport Tygodniowy Kable: {stats["start_date"].strftime("%d.%m")} - {stats["end_date"].strftime("%d.%m")}',
            recipients=['a.bortniczuk@grupaeltron.pl'],
            html=html_content
        )
        
        mail.send(msg)
        flash('Raport tygodniowy został wysłany na a.bortniczuk@grupaeltron.pl', 'success')
        
    except Exception as e:
        print(f"Error sending weekly report: {e}")
        traceback.print_exc()
        flash(f'Błąd podczas wysyłania raportu: {str(e)}', 'danger')
        
    return redirect(url_for('admin.users_list'))
