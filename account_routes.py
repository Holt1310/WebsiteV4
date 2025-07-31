"""
Account management routes for the Tech Guides website.
This module handles user account operations including profile updates,
password changes, and account deletion.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps

# Import database utilities
try:
    from db_utils import get_user_by_username, update_user_profile, change_user_password, delete_user, authenticate_user
except ImportError:
    print("Warning: db_utils not found, using fallback database functions")
    # Fallback imports for compatibility
    import sqlite3
    from datetime import datetime
    from werkzeug.security import check_password_hash, generate_password_hash

account_bp = Blueprint('account', __name__)

def login_required(f):
    """Decorator to require login for account operations."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in to access your account.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@account_bp.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    """Display and handle account management."""
    username = session.get('username')
    
    if not username:
        flash('Session expired. Please log in again.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        print(f"DEBUG: Account POST request received for user: {username}")
        
        try:
            # Get form data
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            external_features = 1 if request.form.get('external_features') else 0
            
            print(f"DEBUG: Form data - first_name: '{first_name}', last_name: '{last_name}', external_features: {external_features}")
            
            # Prepare data for update
            update_data = {
                'first_name': first_name,
                'last_name': last_name,
                'external_features': external_features
            }
            
            print(f"DEBUG: Prepared update data: {update_data}")
            
            # Update user profile
            try:
                success, message = update_user_profile(username, update_data)
                
                if success:
                    print(f"DEBUG: Successfully updated profile for {username}")
                    # Update session data
                    session['first'] = first_name
                    session['last'] = last_name
                    flash('Account updated successfully!', 'success')
                else:
                    print(f"DEBUG: Failed to update profile for {username}: {message}")
                    flash(f'Update failed: {message}', 'error')
                    
            except Exception as e:
                print(f"DEBUG: Exception during profile update for {username}: {e}")
                flash('An error occurred while updating your account.', 'error')
                
        except Exception as e:
            print(f"DEBUG: Exception during account POST processing for {username}: {e}")
            flash('An error occurred while processing your request.', 'error')
        
        return redirect(url_for('account.account'))
    
    # GET request - display account page
    try:
        user = get_user_by_username(username)
        if not user:
            flash('User data not found. Please try logging in again.', 'error')
            # Don't redirect to login, just show empty account page with error
            user = {
                'username': username,
                'first_name': session.get('first', ''),
                'last_name': session.get('last', ''),
                'external_features': 0
            }
            
        print(f"DEBUG: Retrieved user data for {username}: {user}")
        return render_template('account.html', user=user)
        
    except Exception as e:
        print(f"DEBUG: Error retrieving user data for {username}: {e}")
        # Create fallback user data from session
        user = {
            'username': username,
            'first_name': session.get('first', ''),
            'last_name': session.get('last', ''),
            'external_features': 0
        }
        flash('Using basic account data due to database error.', 'warning')
        return render_template('account.html', user=user)

@account_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Handle password change requests."""
    username = session.get('username')
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    print(f"DEBUG: Password change request for user: {username}")
    
    # Validation
    if not all([current_password, new_password, confirm_password]):
        flash('All password fields are required.', 'error')
        return redirect(url_for('account.account'))
    
    if new_password != confirm_password:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('account.account'))
    
    if not new_password or len(new_password) < 6:
        flash('Password must be at least 6 characters long.', 'error')
        return redirect(url_for('account.account'))
    
    try:
        success, message = change_user_password(username, current_password, new_password)
        
        if success:
            print(f"DEBUG: Password changed successfully for {username}")
            flash('Password changed successfully!', 'success')
        else:
            print(f"DEBUG: Password change failed for {username}: {message}")
            flash(message, 'error')
            
    except Exception as e:
        print(f"DEBUG: Exception during password change for {username}: {e}")
        flash('An error occurred while changing your password.', 'error')
    
    return redirect(url_for('account.account'))

@account_bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Handle account deletion requests."""
    username = session.get('username')
    password = request.form.get('password')
    
    print(f"DEBUG: Account deletion request for user: {username}")
    
    if not password:
        flash('Password is required to delete your account.', 'error')
        return redirect(url_for('account.account'))
    
    try:
        # First verify the password
        auth_success, _ = authenticate_user(username, password)
        
        if not auth_success:
            flash('Incorrect password. Account not deleted.', 'error')
            return redirect(url_for('account.account'))
        
        # Delete the account
        success, message = delete_user(username)
        
        if success:
            print(f"DEBUG: Account deleted successfully for {username}")
            # Clear session
            session.clear()
            flash('Your account has been deleted successfully.', 'success')
            return redirect(url_for('login'))
        else:
            print(f"DEBUG: Account deletion failed for {username}: {message}")
            flash(f'Account deletion failed: {message}', 'error')
            
    except Exception as e:
        print(f"DEBUG: Exception during account deletion for {username}: {e}")
        flash('An error occurred while deleting your account.', 'error')
    
    return redirect(url_for('account.account'))


@account_bp.route('/account/external-tools', methods=['GET', 'POST'])
@login_required
def manage_user_external_tools():
    """Manage user's personal external tools."""
    username = session.get('username')
    
    # Check if user tools are allowed
    try:
        # Import here to avoid circular imports
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from app import load_external_tools_config
        
        config = load_external_tools_config()
        if not config.get('settings', {}).get('allow_user_tools', True):
            flash('User external tools are not enabled on this server.', 'error')
            return redirect(url_for('account.account'))
        
        max_tools = config.get('settings', {}).get('max_user_tools', 10)
        
    except Exception as e:
        print(f"Error checking external tools config: {e}")
        flash('Error accessing external tools configuration.', 'error')
        return redirect(url_for('account.account'))
    
    # Import database functions
    try:
        from db_utils import (get_user_external_tools, create_user_external_tool, 
                             update_user_external_tool, delete_user_external_tool, 
                             toggle_user_external_tool)
    except ImportError:
        flash('Database utilities not available.', 'error')
        return redirect(url_for('account.account'))
    
    error = None
    success = None
    
    if request.method == 'POST':
        action = request.form.get('action', '')
        
        try:
            if action == 'add_tool':
                # Get current tool count
                current_tools = get_user_external_tools(username)
                if len(current_tools) >= max_tools:
                    error = f"Maximum {max_tools} tools allowed per user"
                else:
                    tool_data = {
                        'tool_id': request.form.get('tool_id', '').strip(),
                        'name': request.form.get('name', '').strip(),
                        'description': request.form.get('description', '').strip(),
                        'icon': request.form.get('icon', 'bi bi-gear').strip(),
                        'type': request.form.get('type', 'executable'),
                        'executable_path': request.form.get('executable_path', '').strip(),
                        'website_url': request.form.get('website_url', '').strip(),
                        'parameters': request.form.get('parameters', '').strip(),
                        'is_enabled': bool(request.form.get('is_enabled'))
                    }
                    
                    # Validate required fields
                    if not all([tool_data['tool_id'], tool_data['name']]):
                        error = "Tool ID and name are required"
                    elif tool_data['type'] == 'website' and not tool_data['website_url']:
                        error = "Website URL is required for website tools"
                    elif tool_data['type'] in ['executable', 'script'] and not tool_data['executable_path']:
                        error = "Executable path is required for executable/script tools"
                    else:
                        # Check for duplicate tool ID
                        existing_ids = [tool['tool_id'] for tool in current_tools]
                        if tool_data['tool_id'] in existing_ids:
                            error = "Tool ID already exists"
                        else:
                            success_flag, message = create_user_external_tool(username, tool_data)
                            if success_flag:
                                success = f"Tool '{tool_data['name']}' added successfully"
                            else:
                                error = message
                        
            elif action == 'update_tool':
                tool_id = request.form.get('tool_id', '')
                tool_data = {
                    'name': request.form.get('name', '').strip(),
                    'description': request.form.get('description', '').strip(),
                    'icon': request.form.get('icon', 'bi bi-gear').strip(),
                    'type': request.form.get('type', 'executable'),
                    'executable_path': request.form.get('executable_path', '').strip(),
                    'website_url': request.form.get('website_url', '').strip(),
                    'parameters': request.form.get('parameters', '').strip(),
                    'is_enabled': bool(request.form.get('is_enabled'))
                }
                
                success_flag, message = update_user_external_tool(username, tool_id, tool_data)
                if success_flag:
                    success = message
                else:
                    error = message
                    
            elif action == 'delete_tool':
                tool_id = request.form.get('tool_id', '')
                success_flag, message = delete_user_external_tool(username, tool_id)
                if success_flag:
                    success = message
                else:
                    error = message
                    
            elif action == 'toggle_tool':
                tool_id = request.form.get('tool_id', '')
                success_flag, message = toggle_user_external_tool(username, tool_id)
                if success_flag:
                    success = message
                else:
                    error = message
                    
        except Exception as e:
            print(f"Error managing user external tool for {username}: {e}")
            error = f"Error: {str(e)}"
    
    # Get user's current tools
    try:
        user_tools = get_user_external_tools(username)
    except Exception as e:
        print(f"Error loading user tools for {username}: {e}")
        user_tools = []
        error = "Failed to load your tools"
    
    return render_template('account_external_tools.html', 
                         user_tools=user_tools, 
                         max_tools=max_tools,
                         current_count=len(user_tools),
                         error=error, 
                         success=success)


@account_bp.route('/api/user-external-tools', methods=['GET'])
@login_required
def api_get_user_external_tools():
    """API endpoint to get user's external tools."""
    username = session.get('username')
    
    try:
        from db_utils import get_user_external_tools
        tools = get_user_external_tools(username)
        
        return jsonify({
            'success': True,
            'tools': tools,
            'count': len(tools)
        })
        
    except Exception as e:
        print(f"Error getting user external tools via API for {username}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
