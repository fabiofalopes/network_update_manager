#!/usr/bin/env python3
"""
NetworkUpdateManager
------------------
Main entry point for the NetworkUpdateManager application.
"""

import sys
import os
import subprocess
from pathlib import Path
import traceback

def is_running_as_executable():
    """Check if running as frozen executable"""
    return getattr(sys, 'frozen', False)

def show_error_message(title, message):
    """Show an error message to the user"""
    if is_running_as_executable():
        # When running as executable, use a GUI dialog
        try:
            from PyQt5.QtWidgets import QApplication, QMessageBox
            app = QApplication([])
            QMessageBox.critical(None, title, message)
        except ImportError:
            # If PyQt5 fails, try Windows-specific dialog
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
            except:
                # Fall back to console
                print(f"{title}: {message}")
    else:
        # When running as script, use console
        print(f"{title}: {message}")

def is_admin():
    """Check if the script is running with administrative privileges"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def run_as_admin():
    """Re-run the script with administrative privileges"""
    try:
        script = sys.argv[0]
        params = ' '.join([f'"{x}"' for x in sys.argv[1:]])
        subprocess.run(f'powershell Start-Process -Verb RunAs python "{script}" {params}')
        return True
    except:
        return False

def main():
    """Main entry point"""
    # Ensure we're in the correct directory
    os.chdir(Path(__file__).parent)
    
    # Add the current directory to the path
    sys.path.insert(0, str(Path(__file__).parent))
    
    # Check for first run (no credentials)
    cred_path = Path(__file__).parent / 'secure' / '.credentials'
    env_path = Path(__file__).parent / '.env'
    
    if not cred_path.exists() or not env_path.exists():
        try:
            show_error_message("First Run Setup", "First run or missing configuration, running setup...")
            from app.setup import run_setup
            run_setup()
            
            # Check if setup was completed
            if not cred_path.exists() or not env_path.exists():
                show_error_message("Setup Error", "Setup was not completed. Exiting.")
                return 1
                
        except Exception as e:
            error_message = f"Error running setup: {e}\n\n{traceback.format_exc()}"
            show_error_message("Setup Error", error_message)
            return 1
    
    # Check if we need admin rights (for writing to Program Files, etc.)
    local_path = None
    try:
        import dotenv
        dotenv.load_dotenv(env_path)
        local_path = os.getenv("LOCAL_UPDATE_PATH")
    except:
        pass
    
    # If the target directory is in a protected location and we're not admin, restart with admin rights
    protected_paths = ["C:\\Program Files", "C:\\Program Files (x86)", "C:\\Windows"]
    if local_path and any(local_path.startswith(p) for p in protected_paths) and not is_admin():
        show_error_message("Admin Rights Required", 
            "Administrative privileges required to write to protected directories.")
        if not run_as_admin():
            show_error_message("Error", "Failed to restart with administrative privileges.")
            return 1
        return 0
    
    # Run the application
    try:
        from app.main import run
        return run()
    except Exception as e:
        error_message = f"Error running application: {e}\n\n{traceback.format_exc()}"
        show_error_message("Application Error", error_message)
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main()) 
    except Exception as e:
        # Catch any uncaught exceptions
        error_message = f"Unhandled exception: {e}\n\n{traceback.format_exc()}"
        show_error_message("Critical Error", error_message)
        sys.exit(1) 