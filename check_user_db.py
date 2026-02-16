from app import create_app
from extensions import db
from models import User
import sys

# Set encoding to utf-8 for console output
sys.stdout.reconfigure(encoding='utf-8')

app = create_app()

with app.app_context():
    print("Searching for 'Paweł Błażewicz'...")
    user = User.query.filter(User.username == 'Paweł Błażewicz').first()
    if user:
        print(f"FOUND: ID: {user.id} | Username: {repr(user.username)} | Email: {repr(user.email)}")
    else:
        print("NOT FOUND by exact match.")
        
        print("Searching via like '%Blazewicz%' (no polish chars)...")
        users = User.query.filter(User.username.like('%Blazewicz%')).all()
        for u in users:
             print(f"MATCH: ID: {u.id} | Username: {repr(u.username)} | Email: {repr(u.email)}")

        print("Searching via like '%Błażewicz%' (polish chars)...")
        users = User.query.filter(User.username.like('%Błażewicz%')).all()
        for u in users:
             print(f"MATCH: ID: {u.id} | Username: {repr(u.username)} | Email: {repr(u.email)}")
