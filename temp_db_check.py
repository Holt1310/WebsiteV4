#!/usr/bin/env python3
"""Quick script to check database tables"""

import sqlite3

try:
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables = cursor.fetchall()
    
    print("Database tables:")
    for table in tables:
        print(f"- {table[0]}")
    
    conn.close()
    
except Exception as e:
    print(f"Error checking database: {e}")
