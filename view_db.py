import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'diagnoses.db')

if not os.path.exists(DB_PATH):
    print("Database not found at:", DB_PATH)
    print("Make sure you've run the app at least once.")
    input("Press Enter to exit...")
    exit()

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

while True:
    os.system('cls')
    print("=" * 60)
    print("   ATS - DATABASE VIEWER")
    print("=" * 60)
    print()
    print("Available tables:")
    print("  1. users")
    print("  2. diagnoses")
    print("  3. system_checks")
    print("  4. chat_messages")
    print("  5. scheduled_scans")
    print("  6. alert_logs")
    print("  7. custom_responses")
    print("  0. Exit")
    print()
    
    choice = input("Choose a table (0-7): ").strip()
    
    tables = {
        '1': 'users',
        '2': 'diagnoses',
        '3': 'system_checks',
        '4': 'chat_messages',
        '5': 'scheduled_scans',
        '6': 'alert_logs',
        '7': 'custom_responses',
    }
    
    if choice == '0':
        break
    
    if choice in tables:
        table = tables[choice]
        os.system('cls')
        print(f"--- {table} ---")
        print()
        
        try:
            cursor.execute(f"SELECT * FROM {table} LIMIT 50")
            rows = cursor.fetchall()
            
            # Column names
            col_names = [desc[0] for desc in cursor.description]
            print(" | ".join(col_names))
            print("-" * 60)
            
            for row in rows:
                print(" | ".join(str(v)[:30] for v in row))
            
            print()
            print(f"Showing up to 50 rows from '{table}'")
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            total = cursor.fetchone()[0]
            print(f"Total rows in table: {total}")
        except Exception as e:
            print(f"Error: {e}")
        
        print()
        input("Press Enter to continue...")

conn.close()
print("Goodbye!")