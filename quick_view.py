import sqlite3
import json
import os
import sys

# Get the correct path
def get_db_path():
    """Get the correct database path"""
    # Try multiple possible locations
    possible_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'diagnostics.db'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'diagnostics.db'),
        os.path.join(os.getcwd(), 'diagnostics.db'),
        os.path.join(os.getcwd(), '..', 'diagnostics.db'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'diagnostics.db'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # If not found, try to find it in the current directory
    for root, dirs, files in os.walk('.'):
        if 'diagnostics.db' in files:
            return os.path.join(root, 'diagnostics.db')
    
    return None

def check_database():
    """Check if database exists and has tables"""
    db_path = get_db_path()
    
    if not db_path:
        print("❌ Database file 'diagnostics.db' not found!")
        print("\n📁 Please make sure you're in the correct directory.")
        print("   Current directory:", os.getcwd())
        print("\n   Try running:")
        print("   cd 'C:\\Users\\Dell\\Desktop\\ATS(Automated Troubleshooting System)'")
        print("   python quick_view.py")
        return False
    
    print(f"✅ Database found at: {db_path}")
    
    # Check if tables exist
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    if not tables:
        print("❌ No tables found in the database!")
        print("   Please run the Flask app first to create tables:")
        print("   python app.py")
        print("   Then click 'Run Diagnostics' to create some data.")
        conn.close()
        return False
    
    print(f"✅ Tables found: {[t[0] for t in tables]}")
    conn.close()
    return db_path

def view_database():
    """View all data in the database with improved formatting"""
    
    db_path = check_database()
    if not db_path:
        return
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("🔍 ATS TROUBLESHOOTING SYSTEM - DATABASE VIEWER")
    print("="*70)
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("\n📊 TABLES IN DATABASE:")
    print("-" * 70)
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"  📁 {table[0]} ({count} records)")
    
    # View diagnoses
    print("\n" + "="*70)
    print("📋 DIAGNOSES TABLE")
    print("="*70)
    
    try:
        cursor.execute("""
            SELECT id, timestamp, system_status, cpu_usage, memory_usage, 
                   disk_usage, network_status, issues_found, issues_fixed, 
                   user_notes, details
            FROM diagnoses 
            ORDER BY timestamp DESC
        """)
        
        diagnoses = cursor.fetchall()
        
        if diagnoses:
            print(f"\n📊 Total Diagnoses: {len(diagnoses)}\n")
            
            for diag in diagnoses:
                print(f"🔹 Diagnosis #{diag[0]}")
                print(f"   📅 Time: {diag[1]}")
                print(f"   📊 Status: {diag[2]}")
                print(f"   💻 CPU: {diag[3]}%")
                print(f"   🧠 Memory: {diag[4]}%")
                print(f"   💾 Disk: {diag[5]}%")
                print(f"   🌐 Network: {diag[6]}")
                print(f"   ⚠️ Issues Found: {diag[7]}")
                print(f"   ✅ Issues Fixed: {diag[8]}")
                if diag[9]:
                    print(f"   📝 Notes: {diag[9]}")
                
                # Parse and show details
                if diag[10]:
                    try:
                        details = json.loads(diag[10])
                        if 'checks' in details:
                            print(f"   🔍 System Checks:")
                            for check in details['checks']:
                                status_icon = "✅" if check['status'] == 'Pass' else "⚠️" if check['status'] == 'Warning' else "❌"
                                print(f"      {status_icon} {check['name']}: {check['status']}")
                        if 'recommendations' in details:
                            print(f"   💡 Recommendations:")
                            for rec in details['recommendations']:
                                print(f"      - {rec}")
                    except json.JSONDecodeError:
                        print(f"   📄 Details: {diag[10][:100]}...")
                print("-" * 50)
        else:
            print("\n❌ No diagnoses found in the database.")
            print("   Click 'Run Diagnostics' in the web app to create some data.")
    except sqlite3.OperationalError as e:
        print(f"❌ Error reading diagnoses: {e}")
    
    # View system checks
    print("\n" + "="*70)
    print("🔍 SYSTEM CHECKS TABLE")
    print("="*70)
    
    try:
        cursor.execute("""
            SELECT id, diagnosis_id, check_name, status, message, timestamp
            FROM system_checks 
            ORDER BY diagnosis_id DESC, id ASC
            LIMIT 30
        """)
        
        checks = cursor.fetchall()
        
        if checks:
            print(f"\n📊 Showing first 30 checks (most recent):\n")
            for check in checks:
                status_icon = "✅" if check[3] == 'Pass' else "⚠️" if check[3] == 'Warning' else "❌"
                print(f"   #{check[0]} (Diag {check[1]}): {status_icon} {check[2]} → {check[3]}")
                print(f"      💬 {check[4]}")
                print()
        else:
            print("\n❌ No system checks found.")
    except sqlite3.OperationalError as e:
        print(f"❌ Error reading system checks: {e}")
    
    # Close connection
    conn.close()
    
    print("\n" + "="*70)
    print("✅ Database viewing complete!")
    print("="*70)

def get_database_stats():
    """Get statistics about the database"""
    db_path = check_database()
    if not db_path:
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("📊 DATABASE STATISTICS")
    print("="*70)
    
    try:
        # Count diagnoses
        cursor.execute("SELECT COUNT(*) FROM diagnoses")
        total = cursor.fetchone()[0]
        print(f"📋 Total Diagnoses: {total}")
        
        if total > 0:
            # Count by status
            cursor.execute("""
                SELECT system_status, COUNT(*) 
                FROM diagnoses 
                GROUP BY system_status
            """)
            status_counts = cursor.fetchall()
            print("\n📊 Diagnoses by Status:")
            for status, count in status_counts:
                emoji = "✅" if status == "Healthy" else "⚠️" if status == "Warning" else "🔴"
                percentage = (count / total) * 100 if total > 0 else 0
                print(f"   {emoji} {status}: {count} ({percentage:.1f}%)")
            
            # Average metrics
            cursor.execute("""
                SELECT 
                    AVG(cpu_usage),
                    AVG(memory_usage),
                    AVG(disk_usage),
                    AVG(issues_found)
                FROM diagnoses
            """)
            avg = cursor.fetchone()
            if avg:
                print("\n📈 Average Metrics:")
                print(f"   💻 CPU Usage: {avg[0]:.1f}%")
                print(f"   🧠 Memory Usage: {avg[1]:.1f}%")
                print(f"   💾 Disk Usage: {avg[2]:.1f}%")
                print(f"   ⚠️ Issues Found: {avg[3]:.1f}")
            
            # Recent diagnoses
            cursor.execute("""
                SELECT system_status, timestamp 
                FROM diagnoses 
                ORDER BY timestamp DESC 
                LIMIT 5
            """)
            recent = cursor.fetchall()
            print("\n🕐 Recent Diagnoses:")
            for status, timestamp in recent:
                print(f"   {timestamp}: {status}")
        else:
            print("\n❌ No diagnoses found. Run some diagnostics first!")
            
    except sqlite3.OperationalError as e:
        print(f"❌ Error: {e}")
        print("   Make sure the database has been initialized by running the Flask app.")
    
    conn.close()
    print("\n" + "="*70)

def export_to_csv():
    """Export database to CSV files"""
    db_path = check_database()
    if not db_path:
        return
    
    import csv
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Export diagnoses
        cursor.execute("SELECT * FROM diagnoses")
        with open('diagnoses_export.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([description[0] for description in cursor.description])
            writer.writerows(cursor.fetchall())
        print("✅ Exported diagnoses to 'diagnoses_export.csv'")
        
        # Export system_checks
        cursor.execute("SELECT * FROM system_checks")
        with open('system_checks_export.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([description[0] for description in cursor.description])
            writer.writerows(cursor.fetchall())
        print("✅ Exported system_checks to 'system_checks_export.csv'")
        
    except sqlite3.OperationalError as e:
        print(f"❌ Error exporting: {e}")
    
    conn.close()

if __name__ == "__main__":
    print("\n" + "="*70)
    print("ATS TROUBLESHOOTING SYSTEM - DATABASE TOOLS")
    print("="*70)
    print("📁 Current Directory:", os.getcwd())
    print("="*70)
    print("1. View Database")
    print("2. View Statistics")
    print("3. Export to CSV")
    print("4. Run All")
    print("="*70)
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == '1':
        view_database()
    elif choice == '2':
        get_database_stats()
    elif choice == '3':
        export_to_csv()
    elif choice == '4':
        view_database()
        get_database_stats()
        export_to_csv()
    else:
        print("❌ Invalid choice. Running View Database...")
        view_database()