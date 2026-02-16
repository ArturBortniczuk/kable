import pandas as pd
import os
import sys

# Mock config to avoid importing the whole app
class Config:
    EXCEL_PATH = os.path.join(os.getcwd(), 'data.xlsx')

try:
    print(f"Reading Excel from: {Config.EXCEL_PATH}")
    df = pd.read_excel(Config.EXCEL_PATH, header=None)
    print("Excel loaded successfully.")
    
    email_by_name = {}
    for _, row in df.iterrows():
        salesperson = row[0]
        email = row[2]
        email_by_name[salesperson] = email
        print(f"Loaded: {salesperson} -> {email}")
        
    target_name = "Paweł Błażewicz"
    if target_name in email_by_name:
        print(f"\nSUCCESS: Found email for {target_name}: {email_by_name[target_name]}")
    else:
        print(f"\nFAILURE: {target_name} not found in mapping.")
        
except Exception as e:
    print(f"Error: {e}")
