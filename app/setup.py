"""
NetworkUpdateManager - Setup Module
----------------------------------
Handles first-run setup and configuration of the application.
"""

import os
import sys
from pathlib import Path
import shutil
import socket
import winreg
import traceback
import getpass
from PyQt5.QtWidgets import (QApplication, QWizard, QWizardPage, QLabel, 
                           QLineEdit, QVBoxLayout, QHBoxLayout, QCheckBox,
                           QPushButton, QFileDialog, QMessageBox, QTimeEdit)
from PyQt5.QtCore import Qt, QTime
from PyQt5.QtGui import QIcon, QPixmap

from app.config import Config

class SetupWizard(QWizard):
    """Setup wizard for first-run configuration"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("NetworkUpdateManager Setup")
        self.setWizardStyle(QWizard.ModernStyle)
        
        # Try to set icon if it exists
        icon_path = Path(__file__).parent / 'icons' / 'updater.ico'
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # Initialize config
        self.config = Config()
        
        # Add pages
        self.addPage(WelcomePage())
        self.addPage(ShareConfigPage(self.config))
        self.addPage(LocalPathPage(self.config))
        self.addPage(SchedulePage(self.config))
        self.addPage(CredentialsPage(self.config))
        self.addPage(SummaryPage(self.config))
        
        # Set window size
        self.resize(600, 400)
        
    def accept(self):
        """Handle wizard completion"""
        try:
            # Create .env file
            self._create_env_file()
            
            # Save credentials securely
            self._save_credentials()
            
            # Create necessary directories
            self._create_directories()
            
            # Save to registry
            self.config.save_to_registry()
            
            # Set auto-start
            self.config.set_autostart(True)
            
            super().accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Setup Error", 
                f"An error occurred during setup:\n{str(e)}")
            traceback.print_exc()
    
    def _create_env_file(self):
        """Create .env file with configuration values"""
        app_dir = Path(__file__).parent.parent
        env_file = app_dir / '.env'
        
        with open(env_file, 'w') as f:
            f.write(f"# NetworkUpdateManager Configuration\n")
            f.write(f"# Created by setup wizard\n\n")
            
            # Network settings
            f.write(f"# Network share settings\n")
            f.write(f"UPDATE_SHARE_PATH={self.config.update_share_path}\n")
            f.write(f"DOMAIN={self.config.domain}\n\n")
            
            # Local paths
            f.write(f"# Local paths\n")
            f.write(f"LOCAL_UPDATE_PATH={self.config.local_update_path}\n")
            f.write(f"APP_EXECUTABLE_PATH={sys.executable}\n")
            f.write(f"APP_PRETTY_NAME=SIGES Updater\n\n")
            
            # Version tracking
            f.write(f"# Version tracking\n")
            f.write(f"VERSION_FILE_PATTERN=SIGES *.txt\n")
            f.write(f"CHECK_FREQUENCY={self.config.check_frequency}\n")
            
            if hasattr(self.config, 'check_hour') and hasattr(self.config, 'check_minute'):
                f.write(f"CHECK_TIME={self.config.check_hour:02d}:{self.config.check_minute:02d}\n")
            else:
                f.write(f"CHECK_TIME=08:00\n")
                
            f.write(f"CHECK_INTERVAL={self.config.check_interval}\n\n")
            
            # Update settings
            f.write(f"# Update settings\n")
            f.write(f"RETRY_INTERVAL=60\n")
            f.write(f"MAX_RETRIES=3\n\n")
            
            # Logging
            f.write(f"# Logging\n")
            f.write(f"LOG_LEVEL=INFO\n\n")
            
            # Icons
            f.write(f"# Icons\n")
            f.write(f"TRAY_ICON_PATH=app/icons/updater.ico\n")
    
    def _save_credentials(self):
        """Save credentials securely"""
        if hasattr(self.config, 'username') and hasattr(self.config, 'password'):
            self.config.save_credentials(self.config.username, self.config.password)
    
    def _create_directories(self):
        """Create necessary directories"""
        app_dir = Path(__file__).parent.parent
        
        # Create logs directory
        logs_dir = app_dir / 'logs'
        logs_dir.mkdir(exist_ok=True)
        
        # Create secure directory for credentials
        secure_dir = app_dir / 'secure'
        secure_dir.mkdir(exist_ok=True)
        
        # Ensure local update path exists if possible
        try:
            local_path = Path(self.config.local_update_path)
            local_path.mkdir(exist_ok=True, parents=True)
        except Exception:
            # Local path might require admin rights, let the main app handle it
            pass

class WelcomePage(QWizardPage):
    """Welcome page for the setup wizard"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to NetworkUpdateManager")
        self.setSubTitle("This wizard will help you set up the NetworkUpdateManager application.")
        
        layout = QVBoxLayout()
        label = QLabel(
            "NetworkUpdateManager monitors a network share for updates and "
            "keeps your local files in sync with the latest versions available.\n\n"
            "This setup wizard will guide you through:\n"
            "• Configuring the network share connection\n"
            "• Setting up local update paths\n"
            "• Scheduling automatic update checks\n"
            "• Setting credentials for share access\n\n"
            "Click Next to continue."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        
        # Try to add logo
        logo_path = Path(__file__).parent / 'icons' / 'updater.ico'
        if logo_path.exists():
            logo_label = QLabel()
            pixmap = QPixmap(str(logo_path))
            logo_label.setPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            logo_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(logo_label)
        
        self.setLayout(layout)

class ShareConfigPage(QWizardPage):
    """Page for configuring network share settings"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        
        self.setTitle("Network Share Configuration")
        self.setSubTitle("Configure the network share where updates are stored.")
        
        layout = QVBoxLayout()
        
        # Share path input
        share_layout = QHBoxLayout()
        share_label = QLabel("Network Share Path:")
        self.share_path_input = QLineEdit()
        self.share_path_input.setPlaceholderText("\\\\server\\share\\path")
        
        # Use a default value if possible
        hostname = socket.gethostname()
        domain = os.environ.get('USERDOMAIN', 'WORKGROUP')
        self.share_path_input.setText(f"\\\\{hostname}\\updates")
        
        share_layout.addWidget(share_label)
        share_layout.addWidget(self.share_path_input)
        layout.addLayout(share_layout)
        
        # Domain input
        domain_layout = QHBoxLayout()
        domain_label = QLabel("Domain:")
        self.domain_input = QLineEdit()
        self.domain_input.setText(domain)
        
        domain_layout.addWidget(domain_label)
        domain_layout.addWidget(self.domain_input)
        layout.addLayout(domain_layout)
        
        # Test connection button
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.test_connection)
        layout.addWidget(self.test_btn)
        
        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def validatePage(self):
        """Validate the page before proceeding"""
        # Save values to config
        self.config.update_share_path = self.share_path_input.text()
        self.config.domain = self.domain_input.text()
        
        # Basic validation
        if not self.config.update_share_path.startswith('\\\\'):
            QMessageBox.warning(self, "Invalid Path", 
                "Network share path must be in UNC format (\\\\server\\share).")
            return False
        
        return True
    
    def test_connection(self):
        """Test the connection to the network share"""
        # Set status label
        self.status_label.setText("Testing connection...")
        self.status_label.setStyleSheet("color: blue;")
        QApplication.processEvents()
        
        # Save current values to config temporarily
        self.config.update_share_path = self.share_path_input.text()
        self.config.domain = self.domain_input.text()
        
        try:
            # Try to use Windows explorer to test connection
            # This will prompt for credentials if needed
            import subprocess
            subprocess.run(f'explorer "{self.config.update_share_path}"', 
                           shell=True, 
                           timeout=5)
            
            # Update status
            self.status_label.setText("Connection test initiated. Check if Explorer opened the share.")
            self.status_label.setStyleSheet("color: green;")
            
        except Exception as e:
            # Update status
            self.status_label.setText(f"Connection test failed: {str(e)}")
            self.status_label.setStyleSheet("color: red;")

class LocalPathPage(QWizardPage):
    """Page for configuring local update paths"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        
        self.setTitle("Local Path Configuration")
        self.setSubTitle("Configure the local path where updates will be stored.")
        
        layout = QVBoxLayout()
        
        # Local path input
        local_layout = QHBoxLayout()
        local_label = QLabel("Local Update Path:")
        self.local_path_input = QLineEdit()
        self.local_path_input.setPlaceholderText("C:\\Users\\Public\\Digitalis\\PRODUCAO")
        self.local_path_input.setText("C:\\Users\\Public\\Digitalis\\PRODUCAO")
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_local_path)
        
        local_layout.addWidget(local_label)
        local_layout.addWidget(self.local_path_input)
        local_layout.addWidget(browse_btn)
        layout.addLayout(local_layout)
        
        # Version file pattern
        version_layout = QHBoxLayout()
        version_label = QLabel("Version File Pattern:")
        self.version_pattern_input = QLineEdit()
        self.version_pattern_input.setText("SIGES *.txt")
        self.version_pattern_input.setToolTip("Pattern to match version files (e.g., 'SIGES *.txt')")
        
        version_layout.addWidget(version_label)
        version_layout.addWidget(self.version_pattern_input)
        layout.addLayout(version_layout)
        
        # Warning about admin rights
        warning_label = QLabel(
            "Note: If the local path is in a protected location like Program Files, "
            "the application will need to run with administrative privileges."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #CC7000;")
        layout.addWidget(warning_label)
        
        self.setLayout(layout)
    
    def validatePage(self):
        """Validate the page before proceeding"""
        # Save values to config
        self.config.local_update_path = self.local_path_input.text()
        self.config.version_file_pattern = self.version_pattern_input.text()
        
        # Basic validation
        if not self.config.local_update_path:
            QMessageBox.warning(self, "Invalid Path", 
                "Please specify a valid local update path.")
            return False
        
        # Check if the path exists or can be created
        try:
            path = Path(self.config.local_update_path)
            if not path.exists():
                # Try to create the directory
                try:
                    path.mkdir(exist_ok=True, parents=True)
                except PermissionError:
                    # Will need admin rights
                    result = QMessageBox.warning(
                        self, "Permission Required",
                        f"The path '{self.config.local_update_path}' requires administrative "
                        f"privileges to create. The application will need to run as administrator.\n\n"
                        f"Do you want to continue with this path?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    
                    if result == QMessageBox.No:
                        return False
        except Exception as e:
            QMessageBox.warning(self, "Path Error", 
                f"Error checking path: {str(e)}")
            return False
        
        return True
    
    def browse_local_path(self):
        """Browse for local update path"""
        current_path = self.local_path_input.text()
        path = QFileDialog.getExistingDirectory(
            self, "Select Local Update Path", current_path)
        
        if path:
            self.local_path_input.setText(path)

class SchedulePage(QWizardPage):
    """Page for configuring update schedule"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        
        self.setTitle("Update Schedule Configuration")
        self.setSubTitle("Configure when the application should check for updates.")
        
        layout = QVBoxLayout()
        
        # Daily schedule option
        self.daily_radio = QCheckBox("Check daily at:")
        self.daily_radio.setChecked(True)
        layout.addWidget(self.daily_radio)
        
        # Time picker for daily schedule
        time_layout = QHBoxLayout()
        self.time_edit = QTimeEdit()
        self.time_edit.setTime(QTime(8, 0))  # Default to 8:00 AM
        time_layout.addWidget(self.time_edit)
        time_layout.addStretch()
        layout.addLayout(time_layout)
        
        # Interval schedule option
        interval_layout = QHBoxLayout()
        self.interval_radio = QCheckBox("Check every:")
        self.interval_input = QLineEdit()
        self.interval_input.setText("60")
        self.interval_input.setEnabled(False)
        interval_label = QLabel("minutes")
        
        interval_layout.addWidget(self.interval_radio)
        interval_layout.addWidget(self.interval_input)
        interval_layout.addWidget(interval_label)
        layout.addLayout(interval_layout)
        
        # Connect radio buttons
        self.daily_radio.toggled.connect(self.toggle_schedule_type)
        self.interval_radio.toggled.connect(self.toggle_schedule_type)
        
        # Autostart option
        self.autostart_check = QCheckBox("Start application automatically with Windows")
        self.autostart_check.setChecked(True)
        layout.addWidget(self.autostart_check)
        
        self.setLayout(layout)
    
    def toggle_schedule_type(self, checked):
        """Toggle between daily and interval schedule options"""
        if self.sender() == self.daily_radio:
            self.time_edit.setEnabled(checked)
            if checked:
                self.interval_radio.setChecked(False)
        elif self.sender() == self.interval_radio:
            self.interval_input.setEnabled(checked)
            if checked:
                self.daily_radio.setChecked(False)
    
    def validatePage(self):
        """Validate the page before proceeding"""
        # Save values to config
        if self.daily_radio.isChecked():
            time = self.time_edit.time()
            self.config.check_frequency = 'daily'
            self.config.check_hour = time.hour()
            self.config.check_minute = time.minute()
            self.config.check_interval = 24 * 60 * 60  # 24 hours in seconds
        else:
            try:
                interval = int(self.interval_input.text())
                if interval < 1:
                    raise ValueError("Interval must be positive")
                
                self.config.check_frequency = 'minutes'
                self.config.check_interval = interval * 60  # Convert to seconds
            except ValueError as e:
                QMessageBox.warning(self, "Invalid Interval", 
                    f"Please enter a valid positive number for the interval: {str(e)}")
                return False
        
        return True

class CredentialsPage(QWizardPage):
    """Page for configuring network credentials"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        
        self.setTitle("Network Credentials")
        self.setSubTitle("Enter credentials for accessing the network share.")
        
        layout = QVBoxLayout()
        
        # Username input
        username_layout = QHBoxLayout()
        username_label = QLabel("Username:")
        self.username_input = QLineEdit()
        
        # Try to get current username as default
        try:
            default_username = f"{os.environ.get('USERDOMAIN', '')}\\{getpass.getuser()}"
            self.username_input.setText(default_username)
        except:
            pass
            
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        layout.addLayout(username_layout)
        
        # Password input
        password_layout = QHBoxLayout()
        password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)
        
        # Warning about credential storage
        warning_label = QLabel(
            "Note: Credentials will be stored securely using Windows Data Protection API. "
            "They are encrypted with a machine-specific key and can only be decrypted on this computer."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #CC7000;")
        layout.addWidget(warning_label)
        
        self.setLayout(layout)
    
    def validatePage(self):
        """Validate the page before proceeding"""
        # Save values to config
        self.config.username = self.username_input.text()
        self.config.password = self.password_input.text()
        
        # Basic validation
        if not self.config.username:
            QMessageBox.warning(self, "Missing Username", 
                "Please enter a username for network share access.")
            return False
        
        if not self.config.password:
            result = QMessageBox.warning(
                self, "Missing Password",
                "You have not entered a password. Continue anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if result == QMessageBox.No:
                return False
        
        return True

class SummaryPage(QWizardPage):
    """Summary page showing configuration overview"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        
        self.setTitle("Setup Summary")
        self.setSubTitle("Review your configuration settings.")
        
        self.layout = QVBoxLayout()
        self.summary_label = QLabel("Configuration will be displayed here.")
        self.summary_label.setWordWrap(True)
        self.layout.addWidget(self.summary_label)
        
        complete_label = QLabel(
            "Click Finish to complete the setup and start the application."
        )
        complete_label.setWordWrap(True)
        self.layout.addWidget(complete_label)
        
        self.setLayout(self.layout)
    
    def initializePage(self):
        """Initialize the page when it's shown"""
        # Create summary text
        summary = (
            "<b>Network Share:</b><br/>"
            f"• Share Path: {self.config.update_share_path}<br/>"
            f"• Domain: {self.config.domain}<br/><br/>"
            
            "<b>Local Settings:</b><br/>"
            f"• Update Path: {self.config.local_update_path}<br/>"
            f"• Version Pattern: {self.config.version_file_pattern}<br/><br/>"
            
            "<b>Schedule:</b><br/>"
        )
        
        if self.config.check_frequency == 'daily':
            summary += f"• Daily check at {self.config.check_hour:02d}:{self.config.check_minute:02d}<br/><br/>"
        else:
            minutes = self.config.check_interval // 60
            summary += f"• Check every {minutes} minutes<br/><br/>"
        
        summary += (
            "<b>Credentials:</b><br/>"
            f"• Username: {self.config.username}<br/>"
            f"• Password: {'*' * len(self.config.password) if self.config.password else 'None'}<br/>"
        )
        
        self.summary_label.setText(summary)

def run_setup():
    """Run the setup wizard"""
    app = QApplication([])
    wizard = SetupWizard()
    result = wizard.exec_()
    
    # Return True if setup was completed successfully
    return result == QWizard.Accepted

if __name__ == "__main__":
    run_setup() 