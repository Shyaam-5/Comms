import os
import psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

def create_tables():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not found in environment variables.")
        return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        print("Connected to Supabase PostgreSQL.")

        # Create Users Table
        print("Creating users table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Create User Performance Table
        print("Creating user_performance table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_performance (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                module TEXT NOT NULL,
                question_number INTEGER,
                score REAL,
                max_score REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        conn.commit()
        cur.close()
        conn.close()
        print("Tables created successfully.")

    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    create_tables()
