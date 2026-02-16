from app import app
from utils import email_mapping
import sys

target_user = "Test User"

if target_user in email_mapping:
    print(f"SUCCESS: Found {target_user} -> {email_mapping[target_user]}")
else:
    print(f"FAILURE: {target_user} not found in email mapping.")
    print("Available users:", list(email_mapping.keys()))
