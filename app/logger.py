from loguru import logger
import sys
from pathlib import Path
import os

class Logger:
    """Logging manager for application"""
    
    def __init__(self, config):
        self.config = config
        self._setup_logger()
    
    def _setup_logger(self):
        """Configure the logger"""
        # Clear existing handlers
        logger.remove()
        
        # Get log level from config
        log_level = self.config.log_level
        
        # Add stdout handler
        logger.add(
            sys.stdout,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
        
        # Add file handler with rotation
        log_file = self.config.logs_dir / "network_update_manager.log"
        logger.add(
            log_file,
            rotation="1 MB",
            retention="10 days",
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )
        
        # Log system info at startup
        logger.info(f"NetworkUpdateManager started - Version 1.0.0")
        logger.info(f"Running from: {self.config.base_dir}")
        logger.info(f"Update share: {self.config.update_share_path}")
        logger.info(f"Local update path: {self.config.local_update_path}")
        
    def get_logger(self):
        """Return configured logger"""
        return logger 