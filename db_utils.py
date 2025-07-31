"""
Database utilities for the Tech Guides website.
This module provides safe database operations with proper error handling.
"""

import sqlite3
import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    """Context manager for database connections with automatic cleanup."""
    conn = None
    try:
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row  # Enable row factory for dict-like access
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def create_user(username, email, password, first_name, last_name, **kwargs):
    """Create a new user in the database."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if username already exists
            cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                return False, "Username already exists"
            
            # Check if email already exists
            cursor.execute("SELECT email FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                return False, "Email already exists"
            
            # Hash the password
            hashed_password = generate_password_hash(password)
            current_time = datetime.now().isoformat()
            
            # Insert new user with all required fields
            cursor.execute("""
                INSERT INTO users (
                    username, email, password, first_name, last_name,
                    timezone, language, email_notifications, chat_notifications,
                    newsletter, created_at, updated_at, api_enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                username,
                email,
                hashed_password,
                first_name,
                last_name,
                kwargs.get('timezone', 'UTC'),
                kwargs.get('language', 'en'),
                kwargs.get('email_notifications', 1),
                kwargs.get('chat_notifications', 1),
                kwargs.get('newsletter', 0),
                current_time,
                current_time,
                kwargs.get('api_enabled', 0)
            ))
            
            conn.commit()
            return True, "User created successfully"
            
    except sqlite3.IntegrityError as e:
        if 'username' in str(e):
            return False, "Username already exists"
        elif 'email' in str(e):
            return False, "Email already exists"
        else:
            return False, f"Database integrity error: {str(e)}"
    except Exception as e:
        print(f"Error creating user: {e}")
        return False, f"Registration failed: {str(e)}"

def authenticate_user(username, password):
    """Authenticate a user by username and password."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password'], password):
                # Update last login time
                cursor.execute(
                    "UPDATE users SET last_login = ? WHERE username = ?",
                    (datetime.now().isoformat(), username)
                )
                conn.commit()
                
                # Return user data as dict with datetime objects
                user_dict = dict(user)
                # Convert datetime strings back to datetime objects for template compatibility
                for field in ['created_at', 'updated_at', 'last_login']:
                    if user_dict.get(field):
                        try:
                            # Parse ISO format datetime string
                            user_dict[field] = datetime.fromisoformat(user_dict[field])
                        except (ValueError, AttributeError):
                            # If parsing fails, keep as string
                            pass
                # Update last_login to current datetime object since we just updated it
                user_dict['last_login'] = datetime.now()
                
                return True, user_dict
            else:
                return False, None
                
    except Exception as e:
        print(f"Error authenticating user: {e}")
        return False, None

def get_user_by_username(username):
    """Get user data by username."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            
            if user:
                user_dict = dict(user)
                # Convert datetime strings back to datetime objects for template compatibility
                for field in ['created_at', 'updated_at', 'last_login']:
                    if user_dict.get(field):
                        try:
                            # Parse ISO format datetime string
                            user_dict[field] = datetime.fromisoformat(user_dict[field])
                        except (ValueError, AttributeError):
                            # If parsing fails, keep as string
                            pass
                return user_dict
            
            return None
            
    except Exception as e:
        print(f"Error fetching user: {e}")
        return None

def update_user_profile(username, data):
    """Update user profile information."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Build dynamic update query based on provided data
            update_fields = []
            values = []
            
            if 'first_name' in data:
                update_fields.append("first_name = ?")
                values.append(data['first_name'])
            
            if 'last_name' in data:
                update_fields.append("last_name = ?")
                values.append(data['last_name'])
            
            if 'email' in data:
                update_fields.append("email = ?")
                values.append(data['email'])
            
            if 'bio' in data:
                update_fields.append("bio = ?")
                values.append(data['bio'])
            
            if 'timezone' in data:
                update_fields.append("timezone = ?")
                values.append(data['timezone'])
            
            if 'language' in data:
                update_fields.append("language = ?")
                values.append(data['language'])
            
            if 'external_features' in data:
                update_fields.append("external_features = ?")
                values.append(data['external_features'])
            
            # Always update the updated_at timestamp
            update_fields.append("updated_at = ?")
            values.append(datetime.now().isoformat())
            
            # Add username for WHERE clause
            values.append(username)
            
            if update_fields:
                query = f"UPDATE users SET {', '.join(update_fields)} WHERE username = ?"
                cursor.execute(query, values)
                
                rows_affected = cursor.rowcount
                conn.commit()
                
                if rows_affected > 0:
                    return True, f"Successfully updated {rows_affected} row(s)"
                else:
                    return False, f"No user found with username: {username}"
            else:
                return False, "No fields to update"
                
    except Exception as e:
        print(f"Error updating user profile: {e}")
        return False, f"Update failed: {str(e)}"

def change_user_password(username, old_password, new_password):
    """Change user password after verifying old password."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # First verify the old password
            cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            
            if not user:
                return False, "User not found"
            
            if not check_password_hash(user['password'], old_password):
                return False, "Current password is incorrect"
            
            # Hash the new password and update
            hashed_password = generate_password_hash(new_password)
            cursor.execute(
                "UPDATE users SET password = ?, updated_at = ? WHERE username = ?",
                (hashed_password, datetime.now().isoformat(), username)
            )
            
            conn.commit()
            return True, "Password changed successfully"
            
    except Exception as e:
        print(f"Error changing password: {e}")
        return False, f"Password change failed: {str(e)}"

def delete_user(username):
    """Delete a user account."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM users WHERE username = ?", (username,))
            rows_affected = cursor.rowcount
            
            conn.commit()
            
            if rows_affected > 0:
                return True, "Account deleted successfully"
            else:
                return False, "User not found"
                
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False, f"Account deletion failed: {str(e)}"


def get_all_users():
    """Get all users from the database."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT username, email, first_name, last_name, external_features, 
                       created_at, last_login
                FROM users 
                ORDER BY username
            """)
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    'username': row['username'],
                    'email': row['email'],
                    'first': row['first_name'],
                    'last': row['last_name'],
                    'external_features': row['external_features'],
                    'created_at': row['created_at'],
                    'last_login': row['last_login']
                })
            
            return users
            
    except Exception as e:
        print(f"Error getting all users: {e}")
        return []


def toggle_user_external_features(username):
    """Toggle external features for a user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get current state
            cursor.execute("SELECT external_features FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if not row:
                return False, "User not found"
            
            # Toggle the feature
            new_state = 1 if row['external_features'] == 0 else 0
            
            cursor.execute("""
                UPDATE users 
                SET external_features = ?, updated_at = ?
                WHERE username = ?
            """, (new_state, datetime.now().isoformat(), username))
            
            conn.commit()
            
            state_text = "enabled" if new_state == 1 else "disabled"
            return True, f"External features {state_text} for user {username}"
            
    except Exception as e:
        print(f"Error toggling external features for {username}: {e}")
        return False, f"Failed to update user: {str(e)}"


# Custom Data Tables Management Functions

def create_custom_table(table_name, columns, description=""):
    """Create a custom data table with specified columns."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Validate table name (alphanumeric and underscores only)
            import re
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', table_name):
                return False, "Table name must start with a letter and contain only letters, numbers, and underscores"
            
            # Check if table already exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """, (f"custom_{table_name}",))
            
            if cursor.fetchone():
                return False, f"Table '{table_name}' already exists"
            
            # Build CREATE TABLE statement
            column_definitions = []
            for col in columns:
                col_name = col['name']
                col_type = col['type']
                is_required = col.get('required', False)
                is_unique = col.get('unique', False)
                
                # Map column types to SQLite types
                sqlite_type_map = {
                    'string': 'TEXT',
                    'integer': 'INTEGER',
                    'decimal': 'REAL',
                    'boolean': 'INTEGER',
                    'date': 'TEXT',
                    'datetime': 'TEXT',
                    'text': 'TEXT'
                }
                
                sqlite_type = sqlite_type_map.get(col_type, 'TEXT')
                col_def = f"{col_name} {sqlite_type}"
                
                if is_required:
                    col_def += " NOT NULL"
                if is_unique:
                    col_def += " UNIQUE"
                
                column_definitions.append(col_def)
            
            # Add standard columns
            column_definitions.insert(0, "id INTEGER PRIMARY KEY AUTOINCREMENT")
            column_definitions.append("created_at TEXT DEFAULT CURRENT_TIMESTAMP")
            column_definitions.append("updated_at TEXT DEFAULT CURRENT_TIMESTAMP")
            column_definitions.append("created_by TEXT")
            
            create_sql = f"""
                CREATE TABLE custom_{table_name} (
                    {', '.join(column_definitions)}
                )
            """
            
            cursor.execute(create_sql)
            
            # Store table metadata
            cursor.execute("""
                INSERT OR REPLACE INTO custom_tables_metadata 
                (table_name, display_name, description, columns_json, created_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                table_name,
                table_name.replace('_', ' ').title(),
                description,
                str(columns),  # Store as string for now, could use JSON in future
                datetime.now().isoformat(),
                "admin"
            ))
            
            conn.commit()
            return True, f"Table '{table_name}' created successfully"
            
    except Exception as e:
        print(f"Error creating custom table {table_name}: {e}")
        return False, f"Failed to create table: {str(e)}"


def get_custom_tables():
    """Get list of all custom tables."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get tables from metadata
            cursor.execute("""
                SELECT table_name, display_name, description, columns_json, created_at, 
                       (SELECT COUNT(*) FROM custom_tables_metadata) as total_tables
                FROM custom_tables_metadata
                ORDER BY created_at DESC
            """)
            
            tables = []
            for row in cursor.fetchall():
                # Get row count for this table
                try:
                    cursor.execute(f"SELECT COUNT(*) as count FROM custom_{row['table_name']}")
                    row_count = cursor.fetchone()['count']
                except:
                    row_count = 0
                
                # Parse columns (basic parsing since we stored as string)
                columns_str = row['columns_json']
                try:
                    import ast
                    columns = ast.literal_eval(columns_str)
                except:
                    columns = []
                
                tables.append({
                    'table_name': row['table_name'],
                    'display_name': row['display_name'],
                    'description': row['description'],
                    'columns': columns,
                    'row_count': row_count,
                    'created_at': row['created_at']
                })
            
            return tables
            
    except Exception as e:
        print(f"Error getting custom tables: {e}")
        return []


def get_custom_table_data(table_name, limit=100, offset=0):
    """Get data from a custom table."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Validate table exists
            cursor.execute("""
                SELECT table_name FROM custom_tables_metadata 
                WHERE table_name = ?
            """, (table_name,))
            
            if not cursor.fetchone():
                return None, "Table not found"
            
            # Get table data
            cursor.execute(f"""
                SELECT * FROM custom_{table_name} 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            rows = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                rows.append(row_dict)
            
            # Get total count
            cursor.execute(f"SELECT COUNT(*) as total FROM custom_{table_name}")
            total = cursor.fetchone()['total']
            
            return {
                'data': rows,
                'total': total,
                'limit': limit,
                'offset': offset
            }, None
            
    except Exception as e:
        print(f"Error getting table data for {table_name}: {e}")
        return None, f"Error retrieving data: {str(e)}"


def insert_custom_table_row(table_name, data, created_by="admin"):
    """Insert a row into a custom table."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get table metadata to validate columns
            cursor.execute("""
                SELECT columns_json FROM custom_tables_metadata 
                WHERE table_name = ?
            """, (table_name,))
            
            result = cursor.fetchone()
            if not result:
                return False, "Table not found"
            
            # Build INSERT statement
            columns = list(data.keys())
            placeholders = ', '.join(['?' for _ in columns])
            columns_str = ', '.join(columns)
            
            # Add metadata columns
            columns.extend(['created_at', 'updated_at', 'created_by'])
            values = list(data.values())
            current_time = datetime.now().isoformat()
            values.extend([current_time, current_time, created_by])
            
            placeholders = ', '.join(['?' for _ in values])
            columns_str = ', '.join(columns)
            
            cursor.execute(f"""
                INSERT INTO custom_{table_name} ({columns_str})
                VALUES ({placeholders})
            """, values)
            
            conn.commit()
            return True, "Row inserted successfully"
            
    except Exception as e:
        print(f"Error inserting row into {table_name}: {e}")
        return False, f"Failed to insert row: {str(e)}"


def delete_custom_table(table_name):
    """Delete a custom table and its metadata."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Delete the table
            cursor.execute(f"DROP TABLE IF EXISTS custom_{table_name}")
            
            # Delete metadata
            cursor.execute("""
                DELETE FROM custom_tables_metadata 
                WHERE table_name = ?
            """, (table_name,))
            
            conn.commit()
            return True, f"Table '{table_name}' deleted successfully"
            
    except Exception as e:
        print(f"Error deleting custom table {table_name}: {e}")
        return False, f"Failed to delete table: {str(e)}"


def get_custom_table_for_reference(table_name):
    """Get custom table data formatted for other integrations."""
    try:
        result, error = get_custom_table_data(table_name, limit=1000)
        if error or not result:
            return None, error or "No data found"
        
        # Format for easy reference
        formatted_data = {
            'table_name': table_name,
            'display_name': table_name.replace('_', ' ').title(),
            'rows': result['data'],
            'total_rows': result['total']
        }
        
        return formatted_data, None
        
    except Exception as e:
        print(f"Error getting table reference for {table_name}: {e}")
        return None, f"Error: {str(e)}"


def get_custom_table_related_data(table_name, search_column, search_value, return_columns):
    """Get related data from a custom table based on a specific field value."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Validate table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cursor.fetchone():
                return None
            
            # Validate columns exist
            cursor.execute(f"PRAGMA table_info({table_name})")
            available_columns = [row[1] for row in cursor.fetchall()]
            
            if search_column not in available_columns:
                print(f"Search column '{search_column}' not found in table '{table_name}'")
                return None
            
            # Build the query to get related data
            if return_columns:
                # Validate return columns exist
                valid_return_columns = [col for col in return_columns if col in available_columns]
                if not valid_return_columns:
                    print(f"No valid return columns found in table '{table_name}'")
                    return None
                
                columns_str = ', '.join(valid_return_columns)
            else:
                # Return all columns if none specified
                columns_str = '*'
            
            # Execute query to find matching row
            query = f"SELECT {columns_str} FROM {table_name} WHERE {search_column} = ? LIMIT 1"
            cursor.execute(query, (search_value,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Convert row to dictionary
            if return_columns:
                column_names = valid_return_columns
            else:
                column_names = available_columns
            
            result = {}
            for i, value in enumerate(row):
                if i < len(column_names):
                    result[column_names[i]] = value
            
            return result
            
    except Exception as e:
        print(f"Error getting related data from {table_name}: {e}")
        return None


# User External Tools Management Functions

def create_user_external_tool(username, tool_data):
    """Create a new external tool for a user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            current_time = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO user_external_tools 
                (username, tool_id, name, description, icon, type, executable_path, 
                 website_url, parameters, is_enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                username,
                tool_data.get('tool_id'),
                tool_data.get('name'),
                tool_data.get('description', ''),
                tool_data.get('icon', 'bi bi-gear'),
                tool_data.get('type'),
                tool_data.get('executable_path'),
                tool_data.get('website_url'),
                tool_data.get('parameters', ''),
                tool_data.get('is_enabled', 1),
                current_time,
                current_time
            ))
            
            conn.commit()
            return True, "External tool created successfully"
            
    except Exception as e:
        print(f"Error creating user external tool: {e}")
        return False, f"Failed to create tool: {str(e)}"


def get_user_external_tools(username):
    """Get all external tools for a specific user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM user_external_tools 
                WHERE username = ? 
                ORDER BY name
            """, (username,))
            
            tools = []
            for row in cursor.fetchall():
                tools.append(dict(row))
            
            return tools
            
    except Exception as e:
        print(f"Error getting user external tools: {e}")
        return []


def update_user_external_tool(username, tool_id, tool_data):
    """Update an existing user external tool."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_external_tools 
                SET name = ?, description = ?, icon = ?, type = ?, 
                    executable_path = ?, website_url = ?, parameters = ?, 
                    is_enabled = ?, updated_at = ?
                WHERE username = ? AND tool_id = ?
            """, (
                tool_data.get('name'),
                tool_data.get('description', ''),
                tool_data.get('icon', 'bi bi-gear'),
                tool_data.get('type'),
                tool_data.get('executable_path'),
                tool_data.get('website_url'),
                tool_data.get('parameters', ''),
                tool_data.get('is_enabled', 1),
                datetime.now().isoformat(),
                username,
                tool_id
            ))
            
            rows_affected = cursor.rowcount
            conn.commit()
            
            if rows_affected > 0:
                return True, "Tool updated successfully"
            else:
                return False, "Tool not found"
                
    except Exception as e:
        print(f"Error updating user external tool: {e}")
        return False, f"Failed to update tool: {str(e)}"


def delete_user_external_tool(username, tool_id):
    """Delete a user external tool."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM user_external_tools 
                WHERE username = ? AND tool_id = ?
            """, (username, tool_id))
            
            rows_affected = cursor.rowcount
            conn.commit()
            
            if rows_affected > 0:
                return True, "Tool deleted successfully"
            else:
                return False, "Tool not found"
                
    except Exception as e:
        print(f"Error deleting user external tool: {e}")
        return False, f"Failed to delete tool: {str(e)}"


def toggle_user_external_tool(username, tool_id):
    """Toggle the enabled state of a user external tool."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get current state
            cursor.execute("""
                SELECT is_enabled FROM user_external_tools 
                WHERE username = ? AND tool_id = ?
            """, (username, tool_id))
            
            row = cursor.fetchone()
            if not row:
                return False, "Tool not found"
            
            # Toggle the state
            new_state = 1 if row['is_enabled'] == 0 else 0
            
            cursor.execute("""
                UPDATE user_external_tools 
                SET is_enabled = ?, updated_at = ?
                WHERE username = ? AND tool_id = ?
            """, (new_state, datetime.now().isoformat(), username, tool_id))
            
            conn.commit()
            
            state_text = "enabled" if new_state == 1 else "disabled"
            return True, f"Tool {state_text} successfully"
            
    except Exception as e:
        print(f"Error toggling user external tool: {e}")
        return False, f"Failed to toggle tool: {str(e)}"



