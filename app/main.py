import sys
import traceback
import os
from pathlib import Path
import atexit
import socket
import psutil
from PyQt5.QtWidgets import QApplication
from apscheduler.schedulers.background import BackgroundScheduler

# Ensure the app directory is in the path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

# Import app modules
from app.config import Config
from app import logger
from app.share_manager import ShareManager
from app.update_manager import UpdateManager
from app.tray_app import TrayApp

def is_already_running():
    """Check if another instance of the application is already running"""
    # Check by socket binding to a specific port
    try:
        # Try to create a socket and bind to a specific port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 49152))  # Use a high port number
        sock.close()
        
        # Also check for the process by executable name
        app_name = os.path.basename(sys.executable)
        if getattr(sys, 'frozen', False):  # Running as frozen executable
            count = 0
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if proc.info['exe'] == sys.executable and proc.pid != os.getpid():
                        count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
            # If other instances found, prevent running
            if count > 0:
                return True
                
        return False  # No other instance found
    except socket.error:
        # Socket binding failed, another instance is running
        return True

def run():
    """Main entry point for the application"""
    try:
        # Setup logging
        logger.setup_logging()
        
        # Load configuration
        config = Config()
        
        # Check if already running to prevent multiple instances
        if is_already_running():
            logger.log.warning("NetworkUpdateManager is already running. Exiting.")
            return 1
        
        # Initialize the managers
        share_manager = ShareManager(config, logger.log)
        update_manager = UpdateManager(config, logger.log, share_manager)
        
        # Initial version check
        update_manager.check_updates()
        
        # Start the system tray application
        app = QApplication([])
        app.setQuitOnLastWindowClosed(False)
        
        tray_app = TrayApp(config, logger.log, update_manager)
        
        # Setup the update scheduler
        scheduler = BackgroundScheduler()
        
        # Schedule based on frequency setting
        if config.check_frequency == 'daily':
            # Schedule a daily check at the configured time
            scheduler.add_job(
                update_manager.check_and_download_updates,
                'cron',
                hour=config.check_hour,
                minute=config.check_minute,
                id='update_check'
            )
            logger.log.info(f"Scheduled daily update check at {config.check_hour:02d}:{config.check_minute:02d}")
        else:
            # Use interval-based scheduling for hourly or minute-based checks
            scheduler.add_job(
                update_manager.check_and_download_updates,
                'interval', 
                seconds=config.check_interval,
                id='update_check'
            )
            logger.log.info(f"Scheduled update check every {config.check_interval} seconds")
            
        scheduler.start()
        
        # Register cleanup on exit
        atexit.register(scheduler.shutdown)
        
        # Start application event loop
        return app.exec_()
        
    except Exception as e:
        logger.log.critical(f"Critical error in main process: {e}")
        logger.log.exception(e)
        return 1

def handle_first_run():
    """Handle first run setup if needed"""
    # Check if credentials file exists
    app_dir = Path(__file__).parent.parent
    cred_file = app_dir / 'secure' / '.credentials'
    env_file = app_dir / '.env'
    
    if not cred_file.exists() or not env_file.exists():
        print("First run detected - credentials setup required")
        
        # Try to import setup module
        try:
            from app.setup import run_setup
            run_setup()
            
            # Check if setup was completed
            if not cred_file.exists() or not env_file.exists():
                print("Setup was not completed. Exiting.")
                return False
                
        except ImportError:
            print("Setup module not available")
            return False
            
    return True

if __name__ == "__main__":
    # Check for first run
    if not handle_first_run():
        # Show message and exit if setup fails
        print("Setup required. Please run setup.py first.")
        sys.exit(1)
        
    # Run the application
    sys.exit(run()) 