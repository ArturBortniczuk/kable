import pandas as pd
import os

try:
    df = pd.read_excel('data.xlsx', header=None)
    print("All salespersons in Excel:")
    print(df[0].unique())
    
    print("\nFull row for Paweł (if any match):")
    # Search for any string containing "Paweł"
    print(df[df[0].astype(str).str.contains("Paweł", case=False)])
    
except Exception as e:
    print(f"Error: {e}")
