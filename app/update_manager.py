import threading
import time
import schedule
import psutil
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import datetime

class UpdateManager:
    """Manages the update process"""
    
    def __init__(self, config, logger, share_manager):
        self.config = config
        self.logger = logger
        self.share_manager = share_manager
        self.active = False
        self.last_check_time = None
        self.update_thread = None
        self.update_status = "idle"
        self.update_progress = 0
        self.version_info = {
            "local": None,
            "remote": None
        }
        self._setup_scheduler()
    
    def _setup_scheduler(self):
        """Setup scheduled update checks"""
        # Convert check interval from seconds to hours:minutes
        hours = self.config.check_interval // 3600
        minutes = (self.config.check_interval % 3600) // 60
        
        if hours > 0:
            schedule.every(hours).hours.do(self.check_and_download_updates)
        elif minutes > 0:
            schedule.every(minutes).minutes.do(self.check_and_download_updates)
        else:
            schedule.every(max(self.config.check_interval, 30)).seconds.do(self.check_and_download_updates)
            
        self.logger.info(f"Scheduled update checks every {hours}h {minutes}m")
    
    def start(self):
        """Start the update manager"""
        if self.active:
            return
            
        self.active = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        self.logger.info("Update manager started")
        
        # Perform initial update check
        threading.Thread(target=self.check_and_download_updates, daemon=True).start()
    
    def stop(self):
        """Stop the update manager"""
        self.active = False
        if self.update_thread:
            self.update_thread.join(1.0)
        self.logger.info("Update manager stopped")
    
    def _update_loop(self):
        """Main update loop"""
        while self.active:
            schedule.run_pending()
            time.sleep(1)
    
    def check_and_download_updates(self):
        """Check for updates and download if available"""
        self.update_status = "checking"
        self.last_check_time = datetime.datetime.now()
        self.logger.info("Checking for updates...")
        
        try:
            # Check if app is running
            app_running = self._is_app_running()
            
            # Check for updates
            has_updates, updates_list = self.share_manager.check_for_updates()
            
            # Store local and remote version information
            self._update_version_info()
            
            if not has_updates:
                self.update_status = "up_to_date"
                self.logger.info("No updates available")
                return False
            
            # Download updates
            self.update_status = "downloading"
            self.logger.info(f"Downloading {len(updates_list)} updates")
            
            success = self.share_manager.download_updates(updates_list)
            
            if success:
                self.update_status = "downloaded"
                self.logger.info("Updates downloaded successfully")
                
                # Update version info after download
                self._update_version_info()
                
                # Notify about update if app is running
                if app_running:
                    self._notify_app_about_update()
                
                return True
            else:
                self.update_status = "download_failed"
                self.logger.error("Failed to download updates")
                return False
                
        except Exception as e:
            self.update_status = "error"
            self.logger.error(f"Error during update check: {e}")
            return False
    
    def _is_app_running(self):
        """Check if the application is currently running"""
        if not self.config.app_executable_path:
            return False
            
        app_name = Path(self.config.app_executable_path).name
        
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] == app_name:
                self.logger.info(f"Application {app_name} is running")
                return True
                
        self.logger.info(f"Application {app_name} is not running")
        return False
    
    def _notify_app_about_update(self):
        """Notify application about available updates"""
        try:
            # You could implement various notification methods here:
            # 1. Create a flag file in the updates directory
            flag_file = Path(self.config.local_update_path) / "_UPDATE_AVAILABLE"
            with open(flag_file, 'w') as f:
                f.write(datetime.datetime.now().isoformat())
                
            self.logger.info(f"Created update flag: {flag_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to notify application: {e}")
            return False
    
    def _update_version_info(self):
        """Update version information by checking local and remote versions"""
        try:
            local_file, local_version = self.share_manager._get_local_version()
            remote_file, remote_version = self.share_manager._get_remote_version()
            
            self.version_info = {
                "local": local_version,
                "remote": remote_version,
                "local_file": local_file,
                "remote_file": remote_file
            }
            
            self.logger.debug(f"Version info updated: Local={local_version}, Remote={remote_version}")
            
        except Exception as e:
            self.logger.error(f"Error updating version info: {e}")
    
    def get_status(self):
        """Get the current update status"""
        return {
            "status": self.update_status,
            "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
            "update_progress": self.update_progress,
            "version_info": self.version_info
        }
    
    def force_update_check(self):
        """Force an immediate update check"""
        if self.update_status in ["checking", "downloading"]:
            self.logger.info("Update already in progress")
            return False
            
        threading.Thread(target=self.check_and_download_updates, daemon=True).start()
        return True
    
    def check_updates(self):
        """Just check for updates without downloading them"""
        try:
            self.logger.info("Checking for updates...")
            self.update_status = "checking"
            
            # First update version info
            self._update_version_info()
            
            # Check for updates
            if self.share_manager.check_for_updates():
                self.update_status = "update_available"
                self.logger.info("Updates available")
                return True
            else:
                self.update_status = "up_to_date"
                self.logger.info("System is up to date")
                return False
                
        except Exception as e:
            self.update_status = "error"
            self.logger.error(f"Error checking for updates: {e}")
            return False
        finally:
            self.last_check_time = datetime.datetime.now() 