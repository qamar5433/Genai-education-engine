import sqlite3
import os

db_path = os.path.join('backend', 'quizgenius.db')

def check_db():
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Database connected successfully.")
        print(f"Tables found: {[t[0] for t in tables]}")
        
        # Check user count as a sample
        if ('users',) in tables:
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            print(f"Total users in database: {count}")
        else:
            print("Warning: 'users' table not found!")
            
        conn.close()
        print("\nDatabase is healthy and working properly.")
    except Exception as e:
        print(f"Error checking database: {e}")

if __name__ == "__main__":
    check_db()
