import pystray
from PIL import Image, ImageDraw
import threading
import time
import os
from pathlib import Path
import webbrowser
import tempfile
import datetime

class TrayApp:
    """System tray application for the updater"""
    
    def __init__(self, config, logger, update_manager):
        self.config = config
        self.logger = logger
        self.update_manager = update_manager
        self.icon = None
        self.icons = self._load_icons()
        self.current_status = "idle"
    
    def _load_icons(self):
        """Load icons from the configured paths"""
        icons = {}
        base_dir = self.config.base_dir
        
        # Get status icon mapping from config
        status_icons = self.config.status_icons
        
        # First, try to load actual icon files
        for status, icon_path in status_icons.items():
            full_path = base_dir / icon_path
            
            if full_path.exists():
                try:
                    self.logger.debug(f"Loading icon from {full_path}")
                    icons[status] = Image.open(full_path)
                    continue
                except Exception as e:
                    self.logger.warning(f"Failed to load icon from {full_path}: {e}")
            
            # If icon file doesn't exist or loading fails, create a simple colored icon
            icons[status] = self._create_fallback_icon(status)
        
        return icons
    
    def _create_fallback_icon(self, status):
        """Create a simple colored circle icon as fallback"""
        self.logger.debug(f"Creating fallback icon for status: {status}")
        size = 32
        color_map = {
            "idle": (200, 200, 200),  # gray
            "checking": (52, 152, 219),  # blue
            "downloading": (241, 196, 15),  # yellow
            "downloaded": (46, 204, 113),  # green
            "up_to_date": (46, 204, 113),  # green
            "error": (231, 76, 60),  # red
            "download_failed": (231, 76, 60)  # red
        }
        
        color = color_map.get(status, (100, 100, 100))  # default gray
        
        # Create a simple colored circle
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        margin = 2
        draw.ellipse(
            [(margin, margin), (size - margin, size - margin)],
            fill=color
        )
        
        return image
    
    def _get_menu(self):
        """Create the tray icon menu"""
        return pystray.Menu(
            pystray.MenuItem(self.config.app_pretty_name, lambda: None, enabled=False),
            pystray.MenuItem("Check for Updates", self._check_for_updates),
            pystray.MenuItem("Show Status", self._show_status),
            pystray.MenuItem("Configure", self._show_config),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Start with Windows", 
                self._toggle_autostart, 
                checked=lambda item: self.config.get_autostart_status()
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._exit_app)
        )
    
    def _check_for_updates(self):
        """Handle 'Check for Updates' menu item"""
        self.logger.info("Manual update check requested")
        self.update_manager.force_update_check()
    
    def _show_status(self):
        """Show the current status in a temporary HTML file"""
        try:
            status = self.update_manager.get_status()
            version_info = status.get('version_info', {})
            
            # Create a human-readable status message
            status_text = status['status']
            status_class = 'status-ok' if status_text in ['up_to_date', 'downloaded'] else 'status-warn'
            if status_text == 'error':
                status_class = 'status-error'
            
            # Create check schedule text
            if self.config.check_frequency == 'daily':
                check_schedule = f"Daily at {self.config.check_hour:02d}:{self.config.check_minute:02d}"
            else:
                check_schedule = self._format_interval(self.config.check_interval)
            
            # Create HTML content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{self.config.app_pretty_name} Status</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #2c3e50; }}
                    .status-box {{ 
                        border: 1px solid #ddd; 
                        padding: 15px; 
                        border-radius: 5px;
                        margin-top: 20px;
                    }}
                    .status-item {{ 
                        margin-bottom: 10px; 
                        display: flex;
                        justify-content: space-between;
                    }}
                    .status-label {{ font-weight: bold; width: 150px; }}
                    .status-value {{ color: #333; }}
                    .status-ok {{ color: green; }}
                    .status-warn {{ color: orange; }}
                    .status-error {{ color: red; }}
                    .version-highlight {{ 
                        background-color: #f8f9fa; 
                        padding: 10px;
                        border-radius: 5px;
                        margin-top: 20px;
                    }}
                </style>
            </head>
            <body>
                <h1>{self.config.app_pretty_name} Status</h1>
                <div class="status-box">
                    <div class="status-item">
                        <span class="status-label">Status:</span>
                        <span class="status-value {status_class}">{status['status']}</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">Last Check:</span>
                        <span class="status-value">{status['last_check'] if status['last_check'] else 'Never'}</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">Update Path:</span>
                        <span class="status-value">{self.config.update_share_path}</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">Local Update Dir:</span>
                        <span class="status-value">{self.config.local_update_path}</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">Check Schedule:</span>
                        <span class="status-value">{check_schedule}</span>
                    </div>
                </div>
                
                <div class="version-highlight">
                    <h3>Version Information</h3>
                    <div class="status-item">
                        <span class="status-label">Current Version:</span>
                        <span class="status-value">{version_info.get('local', 'Unknown')}</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">Available Version:</span>
                        <span class="status-value">{version_info.get('remote', 'Unknown')}</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">Local Version File:</span>
                        <span class="status-value">{version_info.get('local_file', 'Not found')}</span>
                    </div>
                </div>
                
                <div style="margin-top: 20px; text-align: center; color: #7f8c8d; font-size: 12px;">
                    Generated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                </div>
            </body>
            </html>
            """
            
            # Write to temporary file and open in browser
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html') as f:
                f.write(html_content)
                temp_path = f.name
                
            webbrowser.open(f"file://{temp_path}")
            
        except Exception as e:
            self.logger.error(f"Error showing status: {e}")
    
    def _format_interval(self, seconds):
        """Format interval in seconds to a human-readable string"""
        if seconds >= 86400:  # 24 hours
            days = seconds // 86400
            return f"{days} day{'s' if days > 1 else ''}"
        elif seconds >= 3600:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''}"
        elif seconds >= 60:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''}"
        else:
            return f"{seconds} seconds"
    
    def _show_config(self):
        """Show configuration dialog"""
        try:
            # Could show a GUI configuration dialog here
            # For now, just open the configuration file if it exists
            env_file = Path(self.config.base_dir) / '.env'
            if env_file.exists():
                os.startfile(env_file)
            else:
                self.logger.info("No configuration file found")
                
        except Exception as e:
            self.logger.error(f"Error showing configuration: {e}")
    
    def _exit_app(self):
        """Handle 'Exit' menu item"""
        self.logger.info("Exiting application")
        self.stop()
    
    def _update_icon(self):
        """Update the icon based on the current status"""
        if not self.icon:
            return
            
        status = self.update_manager.get_status()['status']
        if status != self.current_status and status in self.icons:
            self.current_status = status
            self.icon.icon = self.icons[status]
            
            # Update tooltip based on status
            status_texts = {
                "idle": f"{self.config.app_pretty_name} - Idle",
                "checking": f"{self.config.app_pretty_name} - Checking for updates...",
                "downloading": f"{self.config.app_pretty_name} - Downloading updates...",
                "downloaded": f"{self.config.app_pretty_name} - Updates downloaded",
                "up_to_date": f"{self.config.app_pretty_name} - Up to date",
                "error": f"{self.config.app_pretty_name} - Error",
                "download_failed": f"{self.config.app_pretty_name} - Download failed"
            }
            
            self.icon.title = status_texts.get(status, self.config.app_pretty_name)
    
    def _status_monitor(self):
        """Monitor update status in a background thread"""
        while hasattr(self, 'running') and self.running:
            try:
                self._update_icon()
            except Exception as e:
                self.logger.error(f"Error updating tray icon: {e}")
            time.sleep(1)
    
    def start(self):
        """Start the tray application"""
        try:
            # Create and configure the icon
            initial_icon = self.icons["idle"]
            self.icon = pystray.Icon(
                "network_update_manager",
                initial_icon,
                self.config.app_pretty_name,
                self._get_menu()
            )
            
            # Start status monitor thread
            self.running = True
            monitor_thread = threading.Thread(target=self._status_monitor, daemon=True)
            monitor_thread.start()
            
            # Start the icon event loop
            self.logger.info(f"Starting system tray application for {self.config.app_pretty_name}")
            self.icon.run()
            
        except Exception as e:
            self.logger.error(f"Error starting tray application: {e}")
    
    def stop(self):
        """Stop the tray application"""
        self.running = False
        if self.icon:
            self.icon.stop()
            self.logger.info("Stopped system tray application")
    
    def _toggle_autostart(self):
        """Toggle auto-start at Windows startup"""
        try:
            current_status = self.config.get_autostart_status()
            new_status = not current_status
            
            if self.config.set_autostart(new_status):
                self.logger.info(f"Auto-start {'enabled' if new_status else 'disabled'}")
            else:
                self.logger.error("Failed to change auto-start setting")
                
        except Exception as e:
            self.logger.error(f"Error toggling auto-start: {e}") 