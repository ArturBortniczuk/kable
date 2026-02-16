from app import create_app
from extensions import db
from models import User
import pandas as pd
import os
import sys

# Set encoding to utf-8 for console output
sys.stdout.reconfigure(encoding='utf-8')

app = create_app()

with app.app_context():
    print(f"DB URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    try:
        print(f"Engine DB: {db.engine.url.database}")
    except:
        print("Could not get engine db path")

    print("-" * 20)
    print("Checking data.xlsx content from pandas...")
    try:
        excel_path = app.config['EXCEL_PATH']
        print(f"Excel Path: {excel_path}")
        if os.path.exists(excel_path):
            df = pd.read_excel(excel_path, header=None)
            # Row format: Salesperson, Market, Email
            for index, row in df.iterrows():
                try:
                    name = str(row[0])
                    market = str(row[1])
                    email = str(row[2])
                    if "Paweł" in name or "Błażewicz" in name or "Blazewicz" in name:
                        print(f"EXCEL MATCH: Name: {name}, Market: {market}, Email: {email}")
                except Exception as e:
                    pass
        else:
            print("Excel file not found at path.")
    except Exception as e:
        print(f"Error reading excel: {e}")

    print("-" * 20)
    print("Checking DB User table again...")
    user = User.query.filter(User.username.like('%Błażewicz%')).first()
    if user:
         print(f"DB MATCH: {user.username}, {user.email}")
    else:
         print("DB MATCH: None")
