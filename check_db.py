import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'core')))
from core.db import list_all_entries  # Fits your db.py; call for checking entries in autonomous workflows

# 100% complete script to check DB entries (run: python check_db.py)
if __name__ == "__main__":
    print("Checking database entries...")
    entries = list_all_entries()  # Prints table, returns list for further use (e.g., in agents for self-validation)
    if isinstance(entries, str):
        print(entries)  # No entries message
    else:
        print(f"Total entries: {len(entries)}")  # Summary for company monitoring