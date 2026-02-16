from app import create_app
from models import Query, User
from extensions import db
import os
import sys

# Set encoding to utf-8 for console output
sys.stdout.reconfigure(encoding='utf-8')

app = create_app()

# Force using instance DB
instance_db_path = os.path.join(app.root_path, 'instance', 'queries.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{instance_db_path}'

print(f"Checking Query table in: {instance_db_path}")

with app.app_context():
    # Check for queries from Paweł Błażewicz
    queries = Query.query.filter(Query.name == 'Paweł Błażewicz').all()
    print(f"Found {len(queries)} queries from 'Paweł Błażewicz'")
    
    if queries:
        print(f"Latest query ID: {queries[-1].id}, Date: {queries[-1].date_submitted}")

    # Check User count again
    user_count = User.query.count()
    print(f"Total Users in DB: {user_count}")
