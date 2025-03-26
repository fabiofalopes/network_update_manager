from dotenv import load_dotenv
import os
from pathlib import Path
from cryptography.fernet import Fernet
import base64
import hashlib
import json
import sys
import winreg

class Config:
    """Configuration manager with secure credential storage"""
    
    def __init__(self, env_path=None):
        # Set base paths
        self._set_base_paths()
        
        # Load environment variables
        self._load_env(env_path)
        
        # Initialize encryption
        self._init_encryption()
        
        # Load configurations
        self._load_config()
    
    def _set_base_paths(self):
        # Determine if running from frozen executable or script
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            self.base_dir = Path(sys.executable).parent
        else:
            # Running as script
            self.base_dir = Path(__file__).parent.parent
        
        # Set paths
        self.secure_dir = self.base_dir / 'secure'
        self.data_dir = self.base_dir / 'data'
        self.logs_dir = self.base_dir / 'logs'
        
        # Create directories if they don't exist
        self.secure_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
    
    def _load_env(self, env_path=None):
        """Load environment variables from .env file"""
        if env_path:
            load_dotenv(env_path)
        else:
            env_file = self.base_dir / '.env'
            if env_file.exists():
                load_dotenv(env_file)
            else:
                # Try to load from registry
                self._load_from_registry()
    
    def _load_from_registry(self):
        """Load configuration from Windows registry"""
        try:
            registry_key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\NetworkUpdateManager",
                0,
                winreg.KEY_READ
            )
            
            # Load each value from registry
            try:
                i = 0
                while True:
                    name, value, _ = winreg.EnumValue(registry_key, i)
                    os.environ[name] = value
                    i += 1
            except WindowsError:
                # No more values
                pass
                
            winreg.CloseKey(registry_key)
        except WindowsError:
            # Registry key doesn't exist yet
            pass
    
    def _init_encryption(self):
        """Initialize encryption key for secure storage"""
        key_path = self.secure_dir / '.key'
        
        if not key_path.exists():
            # Generate a new key
            machine_id = self._get_machine_id()
            # Derive key from machine ID to make it unique per device
            key_material = hashlib.sha256(machine_id.encode()).digest()
            key = base64.urlsafe_b64encode(key_material)
            
            with open(key_path, 'wb') as key_file:
                key_file.write(key)
        
        # Load the key
        with open(key_path, 'rb') as key_file:
            self.cipher_suite = Fernet(key_file.read())
    
    def _get_machine_id(self):
        """Get a unique machine identifier for deriving encryption key"""
        try:
            with open(r'C:\Windows\System32\config\systemprofile\AppData\Local\Microsoft\Credentials', 'rb') as f:
                machine_data = f.read()
            return hashlib.sha256(machine_data).hexdigest()
        except Exception:
            # Fallback to registry
            try:
                registry_key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Cryptography",
                    0,
                    winreg.KEY_READ | winreg.KEY_WOW64_64KEY
                )
                machine_guid, _ = winreg.QueryValueEx(registry_key, "MachineGuid")
                winreg.CloseKey(registry_key)
                return machine_guid
            except:
                # Last resort: use hostname
                return os.environ.get('COMPUTERNAME', 'UNKNOWN_HOST')
    
    def _load_config(self):
        """Load configuration from environment variables"""
        # Network settings
        self.update_share_path = os.getenv('UPDATE_SHARE_PATH')
        self.domain = os.getenv('DOMAIN', 'ulht')
        
        # Local paths
        self.local_update_path = os.getenv('LOCAL_UPDATE_PATH')
        self.app_executable_path = os.getenv('APP_EXECUTABLE_PATH')
        
        # App display name
        self.app_pretty_name = os.getenv('APP_PRETTY_NAME', 'NetworkUpdateManager')
        
        # Version tracking
        self.version_file_pattern = os.getenv('VERSION_FILE_PATTERN', 'SIGES *.txt')
        self.check_frequency = os.getenv('CHECK_FREQUENCY', 'daily')  # daily, hourly, or minutes
        
        # Daily check time (format: HH:MM in 24-hour format)
        self.check_time = os.getenv('CHECK_TIME', '08:00')
        
        # Update settings
        self.check_interval = int(os.getenv('CHECK_INTERVAL', '300'))  # Default 5 minutes
        
        # If frequency is daily, set the check interval to 24 hours
        if self.check_frequency == 'daily':
            self.check_interval = 24 * 60 * 60  # 24 hours in seconds
        # If frequency is hourly, set the check interval to 1 hour
        elif self.check_frequency == 'hourly':
            self.check_interval = 60 * 60  # 1 hour in seconds
        
        # Parse check time
        try:
            if ':' in self.check_time:
                hour, minute = self.check_time.split(':')
                self.check_hour = int(hour)
                self.check_minute = int(minute)
            else:
                self.check_hour = 8  # Default to 8 AM
                self.check_minute = 0
        except Exception:
            self.check_hour = 8  # Default to 8 AM if parsing fails
            self.check_minute = 0
        
        self.retry_interval = int(os.getenv('RETRY_INTERVAL', '60'))
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        
        # Logging
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # UI Configuration - Icon paths
        self.tray_icon_path = os.getenv('TRAY_ICON_PATH', 'app/icons/updater.ico')
        
        # Status icons (with fallback to main icon)
        self.status_icons = {
            'idle': os.getenv('STATUS_ICON_IDLE', self.tray_icon_path),
            'checking': os.getenv('STATUS_ICON_CHECKING', self.tray_icon_path),
            'downloading': os.getenv('STATUS_ICON_DOWNLOADING', self.tray_icon_path),
            'downloaded': os.getenv('STATUS_ICON_COMPLETED', self.tray_icon_path),
            'up_to_date': os.getenv('STATUS_ICON_COMPLETED', self.tray_icon_path),
            'error': os.getenv('STATUS_ICON_ERROR', self.tray_icon_path),
            'download_failed': os.getenv('STATUS_ICON_ERROR', self.tray_icon_path)
        }
    
    def save_to_registry(self):
        """Save configuration to Windows registry"""
        try:
            # Create or open the registry key
            registry_key = winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\NetworkUpdateManager"
            )
            
            # Save environment variables to registry
            for key in [
                'UPDATE_SHARE_PATH', 'DOMAIN', 'LOCAL_UPDATE_PATH',
                'APP_EXECUTABLE_PATH', 'CHECK_FREQUENCY', 'CHECK_INTERVAL',
                'CHECK_TIME', 'RETRY_INTERVAL', 'MAX_RETRIES', 'LOG_LEVEL',
                'APP_PRETTY_NAME', 'VERSION_FILE_PATTERN'
            ]:
                if key in os.environ:
                    winreg.SetValueEx(
                        registry_key,
                        key,
                        0,
                        winreg.REG_SZ,
                        os.environ[key]
                    )
            
            winreg.CloseKey(registry_key)
            
            # Set auto-start by default
            self.set_autostart(True)
            
            return True
        except Exception:
            return False
    
    def set_autostart(self, enable=True):
        """Set application to start automatically with Windows"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            
            if enable:
                winreg.SetValueEx(
                    key,
                    "NetworkUpdateManager",
                    0,
                    winreg.REG_SZ,
                    self.app_executable_path
                )
            else:
                try:
                    winreg.DeleteValue(key, "NetworkUpdateManager")
                except:
                    pass
                    
            winreg.CloseKey(key)
            return True
        except Exception as e:
            self.logger.error(f"Failed to set autostart: {e}")
            return False
            
    def get_autostart_status(self):
        """Check if application is set to start automatically with Windows"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_READ
            )
            
            try:
                value, _ = winreg.QueryValueEx(key, "NetworkUpdateManager")
                is_enabled = (value == self.app_executable_path)
            except:
                is_enabled = False
                
            winreg.CloseKey(key)
            return is_enabled
        except Exception:
            return False
    
    def encrypt_credentials(self, username, password):
        """Encrypt credentials for secure storage"""
        encrypted_user = self.cipher_suite.encrypt(username.encode())
        encrypted_pass = self.cipher_suite.encrypt(password.encode())
        return encrypted_user, encrypted_pass
    
    def decrypt_credentials(self, encrypted_user, encrypted_pass):
        """Decrypt stored credentials"""
        try:
            username = self.cipher_suite.decrypt(encrypted_user).decode()
            password = self.cipher_suite.decrypt(encrypted_pass).decode()
            return username, password
        except Exception:
            return None, None
    
    def save_credentials(self, username, password):
        """Securely save credentials"""
        encrypted_user, encrypted_pass = self.encrypt_credentials(username, password)
        
        cred_path = self.secure_dir / '.credentials'
        with open(cred_path, 'wb') as f:
            f.write(encrypted_user + b'\n')
            f.write(encrypted_pass)
        
        return True
    
    def load_credentials(self):
        """Load encrypted credentials"""
        cred_path = self.secure_dir / '.credentials'
        
        if not cred_path.exists():
            return None, None
        
        with open(cred_path, 'rb') as f:
            encrypted_user = f.readline().strip()
            encrypted_pass = f.readline().strip()
        
        return self.decrypt_credentials(encrypted_user, encrypted_pass) 