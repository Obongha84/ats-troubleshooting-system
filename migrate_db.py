import sqlite3
import os

def migrate_database():
    """Migrate old database to new schema"""
    
    db_path = 'diagnoses.db'
    
    if not os.path.exists(db_path):
        print("✅ No old database found. A new one will be created automatically.")
        return
    
    print("📊 Migrating database...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check current columns
    cursor.execute("PRAGMA table_info(diagnoses)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"📋 Current columns: {columns}")
    
    # Add missing columns
    new_columns = [
        ("system_name", "VARCHAR(100) DEFAULT 'Local System'"),
        ("disk_health", "VARCHAR(50) DEFAULT 'Good'"),
        ("disk_temperature", "FLOAT DEFAULT 0.0"),
        ("disk_read_errors", "INTEGER DEFAULT 0"),
        ("disk_write_errors", "INTEGER DEFAULT 0"),
        ("disk_power_on_hours", "INTEGER DEFAULT 0"),
        ("disk_bad_sectors", "INTEGER DEFAULT 0"),
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in columns:
            try:
                cursor.execute(f"ALTER TABLE diagnoses ADD COLUMN {col_name} {col_type}")
                print(f"✅ Added column: {col_name}")
            except Exception as e:
                print(f"⚠️ Column {col_name}: {e}")
        else:
            print(f"ℹ️ Column {col_name} already exists")
    
    conn.commit()
    conn.close()
    
    print("✅ Migration complete!")

if __name__ == '__main__':
    migrate_database()