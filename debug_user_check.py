from app import app, db
from models import User
import sys

# Create context
ctx = app.app_context()
ctx.push()

try:
    username = "Roksana Namyślak"
    email = "handelwielkopolski@grupaeltron.pl"

    print(f"Checking for user with username: '{username}'")
    user_by_name = User.query.filter_by(username=username).first()
    if user_by_name:
        print(f"Found user by name: ID={user_by_name.id}, Email={user_by_name.email}")
    else:
        print("No user found with this username.")

    print(f"Checking for user with email: '{email}'")
    user_by_email = User.query.filter_by(email=email).first()
    if user_by_email:
        print(f"Found user by email: ID={user_by_email.id}, Username={user_by_email.username}")
    else:
        print("No user found with this email.")

    # Check all users
    # print("\nAll users:")
    # for u in User.query.all():
    #     print(f"ID: {u.id}, User: {u.username}, Email: {u.email}")

except Exception as e:
    print(f"Error: {e}")
finally:
    ctx.pop()
