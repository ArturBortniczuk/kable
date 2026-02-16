from app import app, db
from models import User
import sys

# Create context
ctx = app.app_context()
ctx.push()

try:
    if not User.query.filter_by(username="Test User").first():
        user = User(username="Test User", email="test@example.com", market="TestMarket")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        print("Test User added.")
    else:
        print("Test User already exists.")
except Exception as e:
    print(f"Error adding user: {e}")
finally:
    ctx.pop()
