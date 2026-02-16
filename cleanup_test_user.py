from app import app, db
from models import User

with app.app_context():
    user = User.query.filter_by(username="Test User").first()
    if user:
        db.session.delete(user)
        db.session.commit()
        print("Test User deleted.")
    else:
        print("Test User not found.")
