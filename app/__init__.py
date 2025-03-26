"""
NetworkUpdateManager
------------------
A system tray application that manages updates from a network share
without requiring the user to have direct access to the share.
"""

from .config import Config
from .logger import Logger
from .share_manager import ShareManager
from .update_manager import UpdateManager
from .tray_app import TrayApp 