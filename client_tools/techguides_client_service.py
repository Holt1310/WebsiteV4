#!/usr/bin/env python3
"""
TechGuides Client Service
A secure client-side service that acts as an API bridge between the web interface
and local system tools, providing authenticated access to external tools.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import requests
import subprocess
import json
import os
import sys
import time
import hashlib
import base64
from datetime import datetime
import socket
import webbrowser
from urllib.parse import urlparse
import pystray
from PIL import Image, ImageDraw


class TechGuidesClientService:
    def __init__(self):
        self.server_url = ""
        self.username = ""
        self.password = ""
        self.session_token = None
        self.is_authenticated = False
        self.is_running = False
        self.polling_thread = None
        self.config_file = "techguides_client_config.json"
        self.tray_icon = None
        self.window_visible = True
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("TechGuides Client Service")
        self.root.geometry("600x700")
        self.root.resizable(True, True)
        
        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.setup_ui()
        self.load_config()
        self.create_tray_icon()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="TechGuides Client Service", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Connection Settings Frame
        conn_frame = ttk.LabelFrame(main_frame, text="Connection Settings", padding="10")
        conn_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        conn_frame.columnconfigure(1, weight=1)
        
        # Server URL
        ttk.Label(conn_frame, text="Server URL:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.server_url_var = tk.StringVar()
        self.server_url_entry = ttk.Entry(conn_frame, textvariable=self.server_url_var, width=40)
        self.server_url_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=2)
        
        # Username
        ttk.Label(conn_frame, text="Username:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.username_var = tk.StringVar()
        self.username_entry = ttk.Entry(conn_frame, textvariable=self.username_var, width=40)
        self.username_entry.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=2)
        
        # Password
        ttk.Label(conn_frame, text="Password:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(conn_frame, textvariable=self.password_var, 
                                       show="*", width=40)
        self.password_entry.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=2)
        
        # Control Buttons Frame
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=3, pady=10)
        
        # Connect Button
        self.connect_btn = ttk.Button(control_frame, text="Connect & Start Service", 
                                     command=self.connect_and_start)
        self.connect_btn.grid(row=0, column=0, padx=(0, 10))
        
        # Disconnect Button
        self.disconnect_btn = ttk.Button(control_frame, text="Disconnect & Stop", 
                                        command=self.disconnect_and_stop, state='disabled')
        self.disconnect_btn.grid(row=0, column=1, padx=(0, 10))
        
        # Open Website Button
        self.website_btn = ttk.Button(control_frame, text="Open Website", 
                                     command=self.open_website, state='disabled')
        self.website_btn.grid(row=0, column=2, padx=(0, 10))
        
        # Save Config Button
        self.save_config_btn = ttk.Button(control_frame, text="Save Config", 
                                         command=self.save_config)
        self.save_config_btn.grid(row=0, column=3, padx=(0, 10))
        
        # Minimize to Tray Button
        self.minimize_btn = ttk.Button(control_frame, text="Minimize to Tray", 
                                      command=self.minimize_to_tray)
        self.minimize_btn.grid(row=0, column=4)
        
        # Status Frame
        status_frame = ttk.LabelFrame(main_frame, text="Service Status", padding="10")
        status_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        status_frame.columnconfigure(1, weight=1)
        
        # Status Label
        ttk.Label(status_frame, text="Status:").grid(row=0, column=0, sticky=tk.W)
        self.status_var = tk.StringVar(value="Disconnected")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                                     foreground="red")
        self.status_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # Server Info
        ttk.Label(status_frame, text="Server:").grid(row=1, column=0, sticky=tk.W)
        self.server_info_var = tk.StringVar(value="Not connected")
        ttk.Label(status_frame, textvariable=self.server_info_var).grid(row=1, column=1, 
                                                                       sticky=tk.W, padx=(10, 0))
        
        # User Info
        ttk.Label(status_frame, text="User:").grid(row=2, column=0, sticky=tk.W)
        self.user_info_var = tk.StringVar(value="Not logged in")
        ttk.Label(status_frame, textvariable=self.user_info_var).grid(row=2, column=1, 
                                                                     sticky=tk.W, padx=(10, 0))
        
        # Available Tools Frame
        tools_frame = ttk.LabelFrame(main_frame, text="Available External Tools", padding="10")
        tools_frame.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(10, 0))
        tools_frame.columnconfigure(0, weight=1)
        tools_frame.rowconfigure(1, weight=1)
        
        # Tools Listbox with Scrollbar
        tools_list_frame = ttk.Frame(tools_frame)
        tools_list_frame.grid(row=1, column=0, sticky="nsew")
        tools_list_frame.columnconfigure(0, weight=1)
        tools_list_frame.rowconfigure(0, weight=1)
        
        self.tools_listbox = tk.Listbox(tools_list_frame, height=6)
        self.tools_listbox.grid(row=0, column=0, sticky="nsew")
        
        tools_scrollbar = ttk.Scrollbar(tools_list_frame, orient="vertical", 
                                       command=self.tools_listbox.yview)
        tools_scrollbar.grid(row=0, column=1, sticky="ns")
        self.tools_listbox.config(yscrollcommand=tools_scrollbar.set)
        
        # Refresh Tools Button
        self.refresh_tools_btn = ttk.Button(tools_frame, text="Refresh Available Tools", 
                                           command=self.refresh_tools, state='disabled')
        self.refresh_tools_btn.grid(row=2, column=0, pady=(10, 0))
        
        # Log Frame
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding="10")
        log_frame.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Log Text Area
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=70)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        # Configure main grid weights
        main_frame.rowconfigure(4, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # Bind Enter key to connect
        self.root.bind('<Return>', lambda e: self.connect_and_start())
        
    def log_message(self, message):
        """Add a timestamped message to the log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        
        # Also print to console
        print(log_entry.strip())
        
    def load_config(self):
        """Load saved configuration"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    
                self.server_url_var.set(config.get('server_url', ''))
                self.username_var.set(config.get('username', ''))
                # Don't save passwords for security
                
                self.log_message("Configuration loaded successfully")
        except Exception as e:
            self.log_message(f"Error loading config: {e}")
            
    def save_config(self):
        """Save current configuration"""
        try:
            config = {
                'server_url': self.server_url_var.get(),
                'username': self.username_var.get(),
                # Don't save password for security
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
            self.log_message("Configuration saved successfully")
            messagebox.showinfo("Success", "Configuration saved!")
            
        except Exception as e:
            self.log_message(f"Error saving config: {e}")
            messagebox.showerror("Error", f"Failed to save config: {e}")
            
    def validate_inputs(self):
        """Validate user inputs"""
        server_url = self.server_url_var.get().strip()
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        
        if not server_url:
            messagebox.showerror("Error", "Server URL is required")
            return False
            
        if not username:
            messagebox.showerror("Error", "Username is required")
            return False
            
        if not password:
            messagebox.showerror("Error", "Password is required")
            return False
            
        # Validate URL format
        try:
            parsed = urlparse(server_url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")
        except Exception:
            messagebox.showerror("Error", "Invalid server URL format. Use http://ip:port or https://domain")
            return False
            
        return True
        
    def connect_and_start(self):
        """Connect to server and start the service"""
        if not self.validate_inputs():
            return
            
        self.server_url = self.server_url_var.get().strip()
        self.username = self.username_var.get().strip()
        self.password = self.password_var.get().strip()
        
        # Ensure URL has proper format
        if not self.server_url.startswith(('http://', 'https://')):
            self.server_url = 'http://' + self.server_url
            
        self.log_message(f"Attempting to connect to {self.server_url}")
        
        # Try to authenticate
        if self.authenticate():
            self.is_running = True
            self.start_polling()
            self.update_ui_state(True)
            self.refresh_tools()
        else:
            self.log_message("Authentication failed")
            
    def disconnect_and_stop(self):
        """Disconnect from server and stop the service"""
        self.is_running = False
        self.is_authenticated = False
        self.session_token = None
        
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=2)
            
        self.update_ui_state(False)
        self.log_message("Service stopped and disconnected")
        
    def authenticate(self):
        """Authenticate with the server"""
        try:
            # First, check if server is reachable
            login_url = f"{self.server_url}/login"
            
            # Test connection
            response = requests.get(self.server_url, timeout=5)
            if response.status_code != 200:
                self.log_message(f"Server returned status {response.status_code}")
                return False
                
            # Attempt login
            login_data = {
                'username': self.username,
                'password': self.password
            }
            
            session = requests.Session()
            response = session.post(login_url, data=login_data, timeout=10, allow_redirects=False)
            
            # Check if login was successful by examining the response
            # Successful login should redirect (status 302) or sometimes return 200
            if response.status_code in [200, 302]:
                self.session = session
                
                # Verify authentication by checking a protected endpoint
                check_url = f"{self.server_url}/check-external-features"
                check_response = self.session.get(check_url, timeout=5)
                
                if check_response.status_code == 200:
                    self.is_authenticated = True
                    self.log_message("Authentication successful")
                    
                    data = check_response.json()
                    if data.get('has_external_features'):
                        self.log_message("External tools access confirmed")
                        return True
                    else:
                        self.log_message("User does not have external tools access enabled")
                        messagebox.showerror("Access Denied", 
                                           "Your account does not have external tools enabled. "
                                           "Please contact an administrator or enable it in your account settings.")
                        return False
                else:
                    self.log_message(f"Authentication verification failed: HTTP {check_response.status_code}")
                    return False
                    
            else:
                self.log_message(f"Login failed - server returned status {response.status_code}")
                # Try to get error message from response
                try:
                    if 'text/html' in response.headers.get('content-type', ''):
                        # For HTML responses, check if there's an error message
                        if 'Invalid username or password' in response.text:
                            self.log_message("Invalid username or password")
                            messagebox.showerror("Login Failed", "Invalid username or password")
                        else:
                            self.log_message("Login failed - check credentials")
                            messagebox.showerror("Login Failed", "Login failed. Please check your credentials.")
                    else:
                        self.log_message(f"Login failed - unexpected response format")
                        messagebox.showerror("Login Failed", f"Login failed with status {response.status_code}")
                except:
                    self.log_message("Login failed - check credentials")
                    messagebox.showerror("Login Failed", "Login failed. Please check your credentials.")
                return False
                
        except requests.exceptions.ConnectionError:
            self.log_message("Connection error - server unreachable")
            messagebox.showerror("Connection Error", "Cannot connect to server. Check URL and network connection.")
            return False
        except requests.exceptions.Timeout:
            self.log_message("Connection timeout")
            messagebox.showerror("Timeout", "Connection to server timed out")
            return False
        except Exception as e:
            self.log_message(f"Authentication error: {e}")
            messagebox.showerror("Error", f"Authentication failed: {e}")
            return False
            
    def start_polling(self):
        """Start polling for command execution requests"""
        if self.polling_thread and self.polling_thread.is_alive():
            return
            
        self.polling_thread = threading.Thread(target=self.poll_for_requests, daemon=True)
        self.polling_thread.start()
        self.log_message("Started polling for command execution requests")
        
    def poll_for_requests(self):
        """Poll server for command execution requests"""
        while self.is_running and self.is_authenticated:
            try:
                # Check for pending commands
                queue_url = f"{self.server_url}/api/client-service/queue"
                response = self.session.get(queue_url, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        queue = data.get('queue', [])
                        
                        # Process each pending command
                        for item in queue:
                            if item.get('status') == 'pending':
                                if item.get('type') == 'command':
                                    command_str = item.get('command', '')
                                    self.log_message(f"Processing command: {command_str}")
                                    
                                    # Execute the command
                                    success = self.execute_command(command_str)
                                    
                                    if success:
                                        # Mark command as completed
                                        self.complete_task(item.get('id'))
                                    else:
                                        self.log_message(f"Command execution failed: {command_str}")
                                else:
                                    # Legacy task support - remove this once fully migrated
                                    tool_id = item.get('tool_id')
                                    if tool_id:
                                        self.log_message(f"Processing legacy task: {tool_id}")
                                        self.execute_tool(tool_id)
                                        self.complete_task(item.get('id'))
                                
                time.sleep(2)  # Poll every 2 seconds
                
            except Exception as e:
                self.log_message(f"Polling error: {e}")
                time.sleep(5)  # Wait longer on error

    def complete_task(self, command_id):
        """Mark a command as completed"""
        try:
            queue_url = f"{self.server_url}/api/client-service/queue"
            data = {
                'action': 'complete',
                'task_id': command_id  # Keep task_id for server compatibility
            }
            
            response = self.session.post(queue_url, json=data, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.log_message(f"Command {command_id} marked as completed")
                else:
                    self.log_message(f"Failed to mark command as completed: {result.get('error')}")
            else:
                self.log_message(f"Failed to complete command: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_message(f"Error completing command {command_id}: {e}")
                
    def refresh_tools(self):
        """Refresh the list of available tools"""
        if not self.is_authenticated:
            return
            
        try:
            tools_url = f"{self.server_url}/api/external-tools"
            response = self.session.get(tools_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('hasAccess'):
                    tools = data.get('tools', [])
                    
                    # Update tools listbox
                    self.tools_listbox.delete(0, tk.END)
                    for tool in tools:
                        if tool.get('enabled', False):
                            display_text = f"{tool.get('name', 'Unknown')} - {tool.get('description', 'No description')}"
                            self.tools_listbox.insert(tk.END, display_text)
                            
                    self.log_message(f"Loaded {len(tools)} available tools")
                else:
                    self.log_message("No access to external tools")
            else:
                self.log_message(f"Failed to load tools: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_message(f"Error refreshing tools: {e}")
            
    def execute_tool(self, tool_id):
        """Execute a specific tool by getting its configuration and running it locally"""
        try:
            # First, get the tool configuration from the server
            tools_url = f"{self.server_url}/api/external-tools"
            response = self.session.get(tools_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('hasAccess'):
                    tools = data.get('tools', [])
                    
                    # Find the tool configuration
                    tool_config = None
                    for tool in tools:
                        if tool.get('id') == tool_id and tool.get('enabled', False):
                            tool_config = tool
                            break
                    
                    if not tool_config:
                        self.log_message(f"Tool {tool_id} not found or disabled")
                        return
                    
                    # Execute the tool based on its type
                    tool_type = tool_config.get('type', 'system')
                    executable = tool_config.get('executable', '')
                    tool_name = tool_config.get('name', tool_id)
                    is_builtin = tool_config.get('builtin', False)
                    
                    if tool_type == 'protocol':
                        # Handle protocol URLs
                        self.log_message(f"Opening protocol URL: {executable}")
                        webbrowser.open(executable)
                        
                    elif tool_type in ['system', 'client_service']:
                        if is_builtin and executable.startswith('builtin:'):
                            self.log_message(f"Unknown built-in tool: {executable}")
                        else:
                            # Execute system command
                            self.log_message(f"Executing {tool_name}: {executable}")
                            subprocess.Popen(executable, shell=True)
                        
                    else:
                        self.log_message(f"Unknown tool type: {tool_type}")
                        return
                        
                    self.log_message(f"Successfully executed {tool_name}")
                    
                else:
                    self.log_message("No access to external tools")
            else:
                self.log_message(f"Failed to get tool configuration: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_message(f"Error executing tool {tool_id}: {e}")
            
    def open_website(self):
        """Open the website in browser"""
        if self.server_url:
            webbrowser.open(self.server_url)
            self.log_message(f"Opened website: {self.server_url}")
            
    def update_ui_state(self, connected):
        """Update UI state based on connection status"""
        if connected:
            self.status_var.set("Connected & Running")
            self.status_label.config(foreground="green")
            self.server_info_var.set(self.server_url)
            self.user_info_var.set(self.username)
            
            self.connect_btn.config(state='disabled')
            self.disconnect_btn.config(state='normal')
            self.website_btn.config(state='normal')
            self.refresh_tools_btn.config(state='normal')
            
            # Disable input fields
            self.server_url_entry.config(state='readonly')
            self.username_entry.config(state='readonly')
            self.password_entry.config(state='readonly')
            
        else:
            self.status_var.set("Disconnected")
            self.status_label.config(foreground="red")
            self.server_info_var.set("Not connected")
            self.user_info_var.set("Not logged in")
            
            self.connect_btn.config(state='normal')
            self.disconnect_btn.config(state='disabled')
            self.website_btn.config(state='disabled')
            self.refresh_tools_btn.config(state='disabled')
            
            # Enable input fields
            self.server_url_entry.config(state='normal')
            self.username_entry.config(state='normal')
            self.password_entry.config(state='normal')
            
            # Clear tools list
            self.tools_listbox.delete(0, tk.END)
            
    def execute_command(self, command_str):
        """Execute a command received from the server."""
        try:
            parts = command_str.split('|')
            if len(parts) < 3 or parts[0] != 'cmd':
                self.log_message(f"Invalid command format: {command_str}")
                return False
            
            command_type = parts[1]
            self.log_message(f"Executing command: {command_type}")
            
            if command_type == 'tool':
                # Handle tool commands: cmd|tool|tool_id|executable|action
                if len(parts) >= 5:
                    tool_id = parts[2]
                    executable = parts[3]
                    action = parts[4]
                    
                    if action == 'launch':
                        if executable == 'standalone':
                            self.log_message(f"Launching standalone {tool_id}")
                        else:
                            self.log_message(f"Launching tool: {executable}")
                            subprocess.Popen(executable, shell=True)
                        return True
                else:
                    self.log_message("Invalid tool command format")
                    return False
                    
            elif command_type == 'system':
                # Handle system commands: cmd|system|command|args...
                if len(parts) >= 3:
                    system_cmd = '|'.join(parts[2:])  # Rejoin the rest as the command
                    self.log_message(f"Executing system command: {system_cmd}")
                    subprocess.Popen(system_cmd, shell=True)
                    return True
                else:
                    self.log_message("Invalid system command format")
                    return False
            else:
                self.log_message(f"Unknown command type: {command_type}")
                return False
                
        except Exception as e:
            self.log_message(f"Error executing command: {e}")
            return False
    
    
    
    def create_tray_icon(self):
        """Create system tray icon"""
        # Create a simple icon image with a tech-themed design
        image = Image.new('RGB', (64, 64), color='#2E86AB')  # Tech blue background
        draw = ImageDraw.Draw(image)
        
        # Draw a gear-like shape to represent tech/tools
        center = 32
        radius = 20
        
        # Draw outer circle
        draw.ellipse([center-radius, center-radius, center+radius, center+radius], 
                    fill='#A23B72', outline='white', width=2)
        
        # Draw inner circle
        inner_radius = 8
        draw.ellipse([center-inner_radius, center-inner_radius, 
                     center+inner_radius, center+inner_radius], 
                    fill='white')
        
        # Draw "TG" text in the center
        draw.text((center-10, center-8), "TG", fill='#2E86AB')
        
        # Create menu for tray icon
        menu = pystray.Menu(
            pystray.MenuItem("Show/Hide Window", self.toggle_window),
            pystray.MenuItem("Open Website", self.open_website_from_tray),
            pystray.MenuItem("Connect", self.connect_and_start),
            pystray.MenuItem("Disconnect", self.disconnect_and_stop),
            pystray.MenuItem("Quit", self.quit_application)
        )
        
        # Create the icon
        self.tray_icon = pystray.Icon("TechGuides", image, "TechGuides Client Service", menu)
        
        # Start the tray icon in a separate thread
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()
    
    def toggle_window(self, icon=None, item=None):
        """Toggle window visibility"""
        if self.window_visible:
            self.root.withdraw()
            self.window_visible = False
        else:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.window_visible = True
    
    def minimize_to_tray(self):
        """Minimize window to system tray"""
        self.root.withdraw()
        self.window_visible = False
        self.log_message("Application minimized to system tray")
    
    def open_website_from_tray(self, icon=None, item=None):
        """Open website from tray icon"""
        if self.is_authenticated and self.server_url:
            webbrowser.open(self.server_url)
    
    def quit_application(self, icon=None, item=None):
        """Quit the application completely"""
        if self.is_running:
            self.disconnect_and_stop()
        
        if self.tray_icon:
            self.tray_icon.stop()
        
        self.root.quit()
        self.root.destroy()
            
    def on_closing(self):
        """Handle window closing - minimize to tray instead of closing"""
        # Instead of closing, just hide the window
        self.root.withdraw()
        self.window_visible = False
        
        # Show a notification that the app is still running
        if self.tray_icon:
            self.log_message("Application minimized to system tray")
            
    def run(self):
        """Run the client service"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log_message("TechGuides Client Service started")
        self.log_message("System tray icon available - click X to minimize to tray")
        self.log_message("Enter server details and click 'Connect & Start Service'")
        self.root.mainloop()


def main():
    """Main entry point"""
    try:
        # Check if another instance is already running
        service = TechGuidesClientService()
        service.run()
    except Exception as e:
        print(f"Error starting client service: {e}")
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
