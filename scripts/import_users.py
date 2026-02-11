import sys
import os
import pandas as pd
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models import User
from utils import generate_password
from config import config

def import_users():
    app = create_app()
    with app.app_context():
        # Create table if not exists
        db.create_all()
        
        print("Importing users from Excel...")
        
        # 1. Special Admins
        admins = [
            {'username': 'Administrator', 'password': 'admin123', 'is_admin': True, 'can_delete': False},
            {'username': 'SuperAdmin', 'password': 'super123', 'is_admin': True, 'can_delete': True}
        ]
        
        for admin_data in admins:
            if not User.query.filter_by(username=admin_data['username']).first():
                user = User(
                    username=admin_data['username'],
                    is_admin=admin_data['is_admin'],
                    can_delete=admin_data['can_delete']
                )
                user.set_password(admin_data['password'])
                db.session.add(user)
                print(f"Added admin: {admin_data['username']}")

        # 2. Excel Users
        try:
            df = pd.read_excel(config.EXCEL_PATH, header=None)
            for _, row in df.iterrows():
                name = row[0]
                market = row[1]
                email = str(row[2]).strip()
                
                # Check for existing
                if User.query.filter_by(username=name).first():
                    print(f"Skipping existing user: {name}")
                    continue
                    
                # Generate initial password (same as current logic)
                initial_password = generate_password(name)
                
                if not initial_password:
                    print(f"Could not generate password for {name}, skipping.")
                    continue

                user = User(
                    username=name,
                    email=email,
                    market=market,
                    is_admin=False,
                    can_delete=False
                )
                user.set_password(initial_password)
                db.session.add(user)
                print(f"Added user: {name} ({email})")
                
            db.session.commit()
            print("\nUser import completed successfully!")
            
        except Exception as e:
            print(f"Error reading Excel: {e}")
            db.session.rollback()

if __name__ == "__main__":
    import_users()
