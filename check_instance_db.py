from app import create_app
from models import User
from extensions import db
import os
import sys

# Set encoding to utf-8 for console output
sys.stdout.reconfigure(encoding='utf-8')

app = create_app()

# Force using instance DB
instance_db_path = os.path.join(app.root_path, 'instance', 'queries.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{instance_db_path}'

print(f"Checking DB at: {instance_db_path}")

with app.app_context():
    user = User.query.filter(User.username == 'Paweł Błażewicz').first()
    if user:
        print(f"FOUND in instance/queries.db: ID: {user.id} | Username: {repr(user.username)} | Email: {repr(user.email)}")
    else:
        print("NOT FOUND in instance/queries.db")
        # List all to be sure
        print("All users in instance DB:")
        for u in User.query.all():
            print(f"{u.username}")

