"""
Create Windows shortcuts for TechGuides Client Service
This script creates desktop shortcuts and startup folder shortcuts
"""

import os
import sys
import winshell
from win32com.client import Dispatch

def create_shortcuts():
    """Create Windows shortcuts for the TechGuides Client Service"""
    
    # Get current directory (client_tools)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Paths to batch files
    normal_start = os.path.join(current_dir, "start_techguides_tray.bat")
    silent_start = os.path.join(current_dir, "start_techguides_silent.bat")
    
    # Desktop paths
    desktop = winshell.desktop()
    
    try:
        # Create desktop shortcut for normal start
        shell = Dispatch('WScript.Shell')
        
        # Normal start shortcut
        shortcut_normal = shell.CreateShortCut(os.path.join(desktop, "TechGuides Client Service.lnk"))
        shortcut_normal.Targetpath = normal_start
        shortcut_normal.WorkingDirectory = current_dir
        shortcut_normal.Description = "TechGuides Client Service with System Tray"
        shortcut_normal.save()
        
        print(f"✓ Created desktop shortcut: TechGuides Client Service.lnk")
        
        # Silent start shortcut
        shortcut_silent = shell.CreateShortCut(os.path.join(desktop, "TechGuides Client (Tray Only).lnk"))
        shortcut_silent.Targetpath = silent_start
        shortcut_silent.WorkingDirectory = current_dir
        shortcut_silent.Description = "TechGuides Client Service - Start in System Tray"
        shortcut_silent.save()
        
        print(f"✓ Created desktop shortcut: TechGuides Client (Tray Only).lnk")
        
        # Ask if user wants to add to startup
        add_startup = input("\nWould you like to add TechGuides to Windows startup? (y/n): ").lower().strip()
        
        if add_startup in ['y', 'yes']:
            # Get startup folder
            startup_folder = winshell.startup()
            
            # Create startup shortcut (silent version)
            shortcut_startup = shell.CreateShortCut(os.path.join(startup_folder, "TechGuides Client Service.lnk"))
            shortcut_startup.Targetpath = silent_start
            shortcut_startup.WorkingDirectory = current_dir
            shortcut_startup.Description = "TechGuides Client Service - Auto Start"
            shortcut_startup.save()
            
            print(f"✓ Added to startup folder: {startup_folder}")
            print("  TechGuides will now start automatically with Windows")
        
        print("\n" + "="*50)
        print("SHORTCUTS CREATED SUCCESSFULLY!")
        print("="*50)
        print("\nDesktop Shortcuts:")
        print("• TechGuides Client Service - Normal start with window")
        print("• TechGuides Client (Tray Only) - Start minimized to tray")
        
        if add_startup in ['y', 'yes']:
            print("\nStartup:")
            print("• Added to Windows startup folder")
            print("• Service will start automatically when Windows boots")
        
        print("\nSystem Tray Usage:")
        print("• Look for blue gear icon with 'TG' in notification area")
        print("• Right-click icon for menu options")
        print("• Double-click to show/hide window")
        print("• Use 'Quit' from tray menu to fully exit")
        
    except Exception as e:
        print(f"Error creating shortcuts: {e}")
        print("You may need to run this script as administrator")
        return False
    
    return True

def main():
    """Main function"""
    print("TechGuides Client Service - Shortcut Creator")
    print("="*50)
    print("This will create Windows shortcuts for easy access\n")
    
    # Check if required modules are available
    try:
        import winshell
        from win32com.client import Dispatch
    except ImportError:
        print("Error: Required modules not found!")
        print("Please install: pip install winshell pywin32")
        input("Press Enter to exit...")
        return
    
    if create_shortcuts():
        print(f"\n✓ All shortcuts created successfully!")
    else:
        print(f"\n✗ Failed to create shortcuts")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
