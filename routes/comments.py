from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from forms import CommentForm
from models import Query, Comment
from extensions import db
from utils import login_required

comments_bp = Blueprint('comments', __name__)

@comments_bp.route('/add-comment', methods=['POST'], endpoint='add_comment')
def add_comment():
    form = CommentForm()
    if form.validate_on_submit():
        query_id = request.form.get('query_id')
        new_comment = Comment(
            content=form.content.data,
            query_id=query_id if query_id else None,
            author=session.get('username')
        )
        db.session.add(new_comment)
        db.session.commit()
        flash('Komentarz został dodany!', 'success')
    else:
        flash('Nie udało się dodać komentarza.', 'danger')
    return redirect(request.referrer)

@comments_bp.route('/mark-comments-read/<int:query_id>', methods=['POST'], endpoint='mark_comments_read')
@login_required
def mark_comments_read(query_id):
    try:
        if request.json and request.json.get('mark_as_read'):
            query = Query.query.get_or_404(query_id)
            for comment in query.comments:
                if not comment.is_read:
                    comment.is_read = True
            db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@comments_bp.route('/toggle-comments-read/<int:query_id>', methods=['POST'], endpoint='toggle_comments_read')
@login_required
def toggle_comments_read(query_id):
    try:
        query = Query.query.get_or_404(query_id)
        is_read = request.json.get('is_read', True)

        for comment in query.comments:
            comment.is_read = is_read

        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
