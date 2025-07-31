"""
Database initialization and management for Tech Guides website.
This module ensures the database and tables are properly set up.
"""

import sqlite3
import os
from datetime import datetime

def init_database():
    """Initialize the database with all required tables and columns."""
    try:
        # Ensure database file exists and is accessible
        db_path = 'database.db'
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create users table with all required columns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                first_name TEXT,
                last_name TEXT,
                bio TEXT,
                timezone TEXT DEFAULT 'UTC',
                language TEXT DEFAULT 'en',
                email_notifications INTEGER DEFAULT 1,
                chat_notifications INTEGER DEFAULT 1,
                newsletter INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                last_login TEXT,
                api_key TEXT,
                api_enabled INTEGER DEFAULT 0,
                external_features INTEGER DEFAULT 0
            )
        ''')
        
        # Create custom tables metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_tables_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                description TEXT,
                columns_json TEXT NOT NULL,
                created_at TEXT,
                updated_at TEXT,
                created_by TEXT
            )
        ''')
        
        # Create user external tools table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_external_tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                tool_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                icon TEXT DEFAULT 'bi bi-gear',
                type TEXT NOT NULL CHECK (type IN ('executable', 'website', 'script')),
                executable_path TEXT,
                website_url TEXT,
                parameters TEXT,
                is_enabled INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(username, tool_id)
            )
        ''')

        
        conn.commit()
        conn.close()
        
        print("Database initialized successfully!")
        return True
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

def test_database_connection():
    """Test database connection and basic operations."""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        
        conn.close()
        print(f"Database connection successful. Users count: {count}")
        return True
        
    except Exception as e:
        print(f"Database connection test failed: {e}")
        return False

def get_table_schema():
    """Get the current users table schema for debugging."""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(users)")
        schema = cursor.fetchall()
        
        conn.close()
        
        print("Users table schema:")
        for column in schema:
            print(f"  {column[1]} ({column[2]}) - {'NOT NULL' if column[3] else 'NULL'} - Default: {column[4]}")
        
        return schema
        
    except Exception as e:
        print(f"Error getting table schema: {e}")
        return None

if __name__ == "__main__":
    print("Initializing database...")
    init_database()
    test_database_connection()
    get_table_schema()
