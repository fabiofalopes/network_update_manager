from smb.SMBConnection import SMBConnection
from pathlib import Path
import os
import socket
import hashlib
import shutil
import time
from datetime import datetime
import win32api
import win32con
import win32security
import ntsecuritycon as con

class ShareManager:
    """Manages connections and operations with network shares"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.connection = None
        self.connected = False
        self.server_name = None
        self.share_name = None
        self.share_path = None
        self._parse_share_path()
    
    def _parse_share_path(self):
        """Parse the UNC share path into components"""
        try:
            # Format: \\server\share\path
            parts = self.config.update_share_path.split('\\')
            self.server_name = parts[2]
            self.share_name = parts[3]
            self.share_path = '\\'.join(parts[4:]) if len(parts) > 4 else ''
            
            self.logger.debug(f"Parsed share path: server={self.server_name}, share={self.share_name}, path={self.share_path}")
        except Exception as e:
            self.logger.error(f"Failed to parse share path: {e}")
    
    def connect(self, username=None, password=None):
        """Connect to the network share"""
        try:
            # If no credentials provided, try to load from config
            if not username or not password:
                username, password = self.config.load_credentials()
                if not username or not password:
                    self.logger.error("No credentials available")
                    return False
            
            self.logger.info(f"Connecting to {self.server_name} as {username}")
            
            # Get local computer name
            client_name = socket.gethostname()
            
            # Create connection
            self.connection = SMBConnection(
                username,
                password,
                client_name,
                self.server_name,
                domain=self.config.domain,
                use_ntlm_v2=True,
                is_direct_tcp=True
            )
            
            # Connect to server
            self.connected = self.connection.connect(self.server_name, 445)
            
            if self.connected:
                self.logger.info(f"Successfully connected to {self.server_name}")
                return True
            else:
                self.logger.error(f"Failed to connect to {self.server_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the network share"""
        if self.connection:
            try:
                self.connection.close()
                self.connected = False
                self.logger.info(f"Disconnected from {self.server_name}")
            except Exception as e:
                self.logger.error(f"Error disconnecting: {e}")
    
    def list_updates(self):
        """List available updates on the share"""
        if not self.ensure_connected():
            return []
            
        try:
            self.logger.info(f"Listing updates in {self.share_name}/{self.share_path}")
            files = self.connection.listPath(self.share_name, self.share_path)
            
            # Filter out directories and system files
            updates = []
            for f in files:
                if f.filename not in ['.', '..'] and not f.isDirectory:
                    updates.append({
                        'filename': f.filename,
                        'size': f.file_size,
                        'create_time': datetime.fromtimestamp(f.create_time).isoformat(),
                        'last_modified': datetime.fromtimestamp(f.last_write_time).isoformat()
                    })
            
            self.logger.info(f"Found {len(updates)} updates")
            return updates
            
        except Exception as e:
            self.logger.error(f"Error listing updates: {e}")
            return []
    
    def ensure_connected(self):
        """Ensure connection to the share is active"""
        if not self.connected or not self.connection:
            return self.connect()
        return True
    
    def download_file(self, filename, local_path=None):
        """Download a file from the share"""
        if not self.ensure_connected():
            return False
            
        try:
            # Determine remote and local paths
            remote_path = f"{self.share_path}/{filename}" if self.share_path else filename
            if not local_path:
                local_path = Path(self.config.local_update_path) / filename
            else:
                local_path = Path(local_path)
                
            # Create parent directories if they don't exist
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use a temporary file for downloading
            temp_path = local_path.with_suffix('.tmp')
            
            self.logger.info(f"Downloading {filename} to {local_path}")
            
            # Download to temporary file
            with open(temp_path, 'wb') as file_obj:
                self.connection.retrieveFile(self.share_name, remote_path, file_obj)
            
            # Verify download integrity
            if self._verify_file(filename, temp_path):
                # Safely replace the original file
                if local_path.exists():
                    # Take ownership if needed
                    try:
                        self._take_ownership(local_path)
                    except Exception as e:
                        self.logger.warning(f"Failed to take ownership of {local_path}: {e}")
                
                shutil.move(str(temp_path), str(local_path))
                self.logger.info(f"Successfully downloaded {filename}")
                return True
            else:
                # Remove temporary file if verification failed
                if temp_path.exists():
                    temp_path.unlink()
                self.logger.error(f"File verification failed for {filename}")
                return False
                
        except Exception as e:
            self.logger.error(f"Download error for {filename}: {e}")
            return False
    
    def _verify_file(self, filename, local_path):
        """Verify file integrity"""
        try:
            # Check file exists
            if not local_path.exists():
                self.logger.error(f"Downloaded file not found: {local_path}")
                return False
                
            # Get local file size
            local_size = local_path.stat().st_size
            
            # Get remote file size
            remote_path = f"{self.share_path}/{filename}" if self.share_path else filename
            file_info = self.connection.getAttributes(self.share_name, remote_path)
            remote_size = file_info.file_size
            
            # Compare sizes
            if local_size != remote_size:
                self.logger.error(f"Size mismatch: local={local_size}, remote={remote_size}")
                return False
                
            # Calculate MD5 hash for downloaded file
            md5_hash = hashlib.md5()
            with open(local_path, 'rb') as file:
                for chunk in iter(lambda: file.read(4096), b''):
                    md5_hash.update(chunk)
            file_hash = md5_hash.hexdigest()
            
            self.logger.debug(f"File verification: {filename}, hash={file_hash}, size={local_size}")
            return True
            
        except Exception as e:
            self.logger.error(f"Verification error: {e}")
            return False
    
    def _take_ownership(self, file_path):
        """Take ownership of a file to enable replacement"""
        try:
            # Get the SID for the current user
            username = win32api.GetUserName()
            user_sid = win32security.LookupAccountName(None, username)[0]
            
            # Open the file and get the security descriptor
            handle = win32security.GetFileSecurity(
                str(file_path),
                win32security.OWNER_SECURITY_INFORMATION
            )
            
            # Set the owner
            win32security.SetSecurityInfo(
                handle,
                win32security.SE_FILE_OBJECT,
                win32security.OWNER_SECURITY_INFORMATION,
                user_sid,
                None, None, None
            )
            
            # Grant full control
            sd = win32security.GetFileSecurity(
                str(file_path),
                win32security.DACL_SECURITY_INFORMATION
            )
            
            dacl = sd.GetSecurityDescriptorDacl()
            dacl.AddAccessAllowedAce(
                win32security.ACL_REVISION,
                con.FILE_ALL_ACCESS,
                user_sid
            )
            
            sd.SetSecurityDescriptorDacl(1, dacl, 0)
            win32security.SetFileSecurity(
                str(file_path),
                win32security.DACL_SECURITY_INFORMATION,
                sd
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error taking ownership: {e}")
            return False
    
    def check_for_updates(self):
        """Check if updates are available"""
        if not self.ensure_connected():
            return False, []
            
        try:
            # First, check if version file exists and compare versions
            has_newer_version, version_info = self._check_version_files()
            
            if not has_newer_version:
                self.logger.info("No newer version available")
                return False, []
                
            # Get list of updates on the share
            remote_files = self.list_updates()
            if not remote_files:
                return False, []
                
            # Check local directory
            local_dir = Path(self.config.local_update_path)
            if not local_dir.exists():
                local_dir.mkdir(parents=True, exist_ok=True)
                
            # Compare with local files
            updates_available = []
            for remote_file in remote_files:
                filename = remote_file['filename']
                local_file = local_dir / filename
                
                # Check if update is needed
                if self._needs_update(remote_file, local_file):
                    updates_available.append(remote_file)
            
            has_updates = len(updates_available) > 0
            self.logger.info(f"Updates available: {has_updates} ({len(updates_available)} files)")
            
            return has_updates, updates_available
            
        except Exception as e:
            self.logger.error(f"Error checking for updates: {e}")
            return False, []
    
    def _check_version_files(self):
        """Check version files to determine if update is needed"""
        try:
            # Get local version first
            local_version_file, local_version = self._get_local_version()
            if not local_version_file or not local_version:
                self.logger.warning("No local version file found, will download updates")
                return True, {"local": None, "remote": None}
            
            # Get remote version
            remote_version_file, remote_version = self._get_remote_version()
            if not remote_version_file or not remote_version:
                self.logger.warning("No remote version file found, cannot determine if update is needed")
                return False, {"local": local_version, "remote": None}
            
            # Compare versions
            need_update = self._compare_versions(local_version, remote_version)
            
            if need_update:
                self.logger.info(f"New version available: {local_version} -> {remote_version}")
            else:
                self.logger.info(f"Already on latest version: {local_version}")
                
            return need_update, {
                "local": local_version, 
                "remote": remote_version,
                "local_file": local_version_file,
                "remote_file": remote_version_file
            }
            
        except Exception as e:
            self.logger.error(f"Error checking version files: {e}")
            return True, {}  # If error occurs, assume update is needed
    
    def _get_local_version(self):
        """Get the current local version from version file"""
        try:
            local_dir = Path(self.config.local_update_path)
            if not local_dir.exists():
                return None, None
                
            # Find version file based on pattern
            from glob import glob
            pattern = self.config.version_file_pattern
            version_files = list(local_dir.glob(pattern))
            
            if not version_files:
                self.logger.warning(f"No local version files found matching pattern: {pattern}")
                return None, None
                
            # Get the latest version file (in case there are multiple)
            latest_file = max(version_files, key=lambda p: p.stat().st_mtime)
            filename = latest_file.name
            
            # Extract version from filename (e.g., 'SIGES 20.0.20-24.txt' -> '20.0.20-24')
            version = self._extract_version_from_filename(filename)
            
            self.logger.debug(f"Local version file: {filename}, version: {version}")
            return filename, version
                
        except Exception as e:
            self.logger.error(f"Error getting local version: {e}")
            return None, None
    
    def _get_remote_version(self):
        """Get the latest version available on the share"""
        try:
            if not self.ensure_connected():
                return None, None
                
            # List all files on share
            remote_files = self.list_updates()
            if not remote_files:
                return None, None
                
            # Filter for version files based on pattern
            pattern = self.config.version_file_pattern.replace('*', '.*')
            import re
            version_pattern = re.compile(pattern, re.IGNORECASE)
            
            version_files = [f for f in remote_files if version_pattern.match(f['filename'])]
            
            if not version_files:
                self.logger.warning(f"No remote version files found matching pattern: {pattern}")
                return None, None
                
            # Get the latest version file (by date)
            latest_file = max(version_files, key=lambda f: f['last_modified'])
            filename = latest_file['filename']
            
            # Extract version from filename
            version = self._extract_version_from_filename(filename)
            
            self.logger.debug(f"Remote version file: {filename}, version: {version}")
            return filename, version
                
        except Exception as e:
            self.logger.error(f"Error getting remote version: {e}")
            return None, None
    
    def _extract_version_from_filename(self, filename):
        """Extract version number from filename"""
        try:
            # Pattern: Find all numeric parts with dots/hyphens between them
            import re
            # This pattern would extract "20.0.20-24" from "SIGES 20.0.20-24.txt"
            version_match = re.search(r'(\d+(\.\d+)*(-\d+)*)', filename)
            
            if version_match:
                return version_match.group(1)
            else:
                # Fallback: just use the filename as version
                self.logger.warning(f"Could not extract version from filename: {filename}")
                return filename
                
        except Exception as e:
            self.logger.error(f"Error extracting version: {e}")
            return filename
    
    def _compare_versions(self, local_version, remote_version):
        """Compare version numbers to determine if update is needed"""
        try:
            if not local_version or not remote_version:
                return True
                
            # Split versions into components
            import re
            
            # Parse version strings into components
            def parse_version(version_str):
                # Split by dots and hyphens
                parts = re.split(r'[.-]', version_str)
                # Convert to integers
                return [int(part) for part in parts if part.isdigit()]
            
            local_parts = parse_version(local_version)
            remote_parts = parse_version(remote_version)
            
            # Compare components one by one
            for i in range(min(len(local_parts), len(remote_parts))):
                if remote_parts[i] > local_parts[i]:
                    return True
                elif remote_parts[i] < local_parts[i]:
                    return False
            
            # If we get here and remote has more components, it's newer
            return len(remote_parts) > len(local_parts)
                
        except Exception as e:
            self.logger.error(f"Error comparing versions: {e}")
            # If comparison fails, assume update is needed
            return True
    
    def _needs_update(self, remote_file, local_path):
        """Check if local file needs to be updated"""
        # If file doesn't exist locally, update is needed
        if not local_path.exists():
            self.logger.debug(f"File doesn't exist locally: {local_path.name}")
            return True
            
        try:
            # Compare file sizes
            local_size = local_path.stat().st_size
            if remote_file['size'] != local_size:
                self.logger.debug(f"Size mismatch for {local_path.name}: remote={remote_file['size']}, local={local_size}")
                return True
                
            # Compare modification times
            remote_time = datetime.fromisoformat(remote_file['last_modified'])
            local_time = datetime.fromtimestamp(local_path.stat().st_mtime)
            
            # If remote file is newer, update is needed
            if remote_time > local_time:
                self.logger.debug(f"Remote file is newer: {local_path.name}")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking if update is needed: {e}")
            # If error occurs, assume update is needed
            return True
    
    def download_updates(self, update_list=None):
        """Download all available updates"""
        if not self.ensure_connected():
            return False
            
        try:
            # If no update list provided, check for updates
            if not update_list:
                has_updates, update_list = self.check_for_updates()
                if not has_updates:
                    self.logger.info("No updates to download")
                    return True
            
            self.logger.info(f"Downloading {len(update_list)} updates")
            
            # Download each update
            success_count = 0
            for update in update_list:
                if self.download_file(update['filename']):
                    success_count += 1
            
            success_rate = success_count / len(update_list) if update_list else 0
            self.logger.info(f"Downloaded {success_count}/{len(update_list)} updates ({success_rate:.0%})")
            
            return success_count == len(update_list)
            
        except Exception as e:
            self.logger.error(f"Error downloading updates: {e}")
            return False 