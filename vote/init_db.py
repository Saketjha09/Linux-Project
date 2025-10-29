#!/usr/bin/env python3
"""Initialize database with demo users and competition"""
import os
import psycopg2
from auth import hash_password

# Database configuration
db_host = os.getenv('DB_HOST', 'db')
db_port = int(os.getenv('DB_PORT', 5432))
db_name = os.getenv('DB_NAME', 'postgres')
db_user = os.getenv('POSTGRES_USER', 'postgres')
db_password = os.getenv('POSTGRES_PASSWORD', 'postgres')

connection_string = f"dbname={db_name} user={db_user} password={db_password} host={db_host} port={db_port}"

def init_db():
    """Initialize database with demo data"""
    try:
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        
        print("[*] Initializing database...")
        
        # Check if admin user exists
        cursor.execute("SELECT id FROM users WHERE username = %s", ('admin',))
        if not cursor.fetchone():
            print("[+] Creating admin user...")
            admin_hash = hash_password('admin123')
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, is_admin) VALUES (%s, %s, %s, %s)",
                ('admin', 'admin@example.com', admin_hash, True)
            )
            conn.commit()
            print("    ✓ Admin user created (username: admin, password: admin123)")
        
        # Check if demo user exists
        cursor.execute("SELECT id FROM users WHERE username = %s", ('user1',))
        if not cursor.fetchone():
            print("[+] Creating demo user...")
            user_hash = hash_password('user123')
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, is_admin) VALUES (%s, %s, %s, %s)",
                ('user1', 'user1@example.com', user_hash, False)
            )
            conn.commit()
            print("    ✓ Demo user created (username: user1, password: user123)")
        
        # Check if demo competition exists
        cursor.execute("SELECT id FROM competitions WHERE name = %s", ('Cats vs Dogs',))
        if not cursor.fetchone():
            print("[+] Creating demo competition...")
            cursor.execute("SELECT id FROM users WHERE username = %s", ('admin',))
            admin_id = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO competitions (name, description, option_a, option_b, created_by, status) VALUES (%s, %s, %s, %s, %s, %s)",
                ('Cats vs Dogs', 'Classic competition between cats and dogs', 'Cats', 'Dogs', admin_id, 'active')
            )
            conn.commit()
            print("    ✓ Demo competition created")
        
        cursor.close()
        conn.close()
        print("\n[✓] Database initialization complete!")
        return True
    
    except Exception as e:
        print(f"[✗] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = init_db()
    exit(0 if success else 1)
