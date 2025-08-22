'''
Usage:

from mylib.common.proj_logger import proj_logger
proj_logger.info("msg")
proj_logger.debug("msg")
proj_logger.error("msg")
'''
import os
import sys
import platform
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

"""
Folder structure:

logs/
|--{name}/
   |--redfish.log
|--accesslog/
   |--redfish.log
|--applog/
   |--redfish.log
"""
class ProjLogger:
    # _instance = None
    _logger = None
    
    # def __new__(cls):
    #     if cls._instance is None:
    #         cls._instance = super().__new__(cls)
    #     return cls._instance
    
    def __init__(self, name="default"):
        self.name = name
        self.log_root = os.getenv("PROJ_LOG_ROOT")
        if platform.system() == 'Windows':
            self.log_root = "logs"

        # formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self.formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        self.log_filename = f"redfish.log"
        self.log_name_root = os.path.join(self.log_root, self.name)
        self.log_filepath = os.path.join(self.log_name_root, self.log_filename)

        if not os.path.exists(self.log_name_root): 
            print(f"Create folder: {self.log_name_root}")
            os.makedirs(self.log_name_root, exist_ok=True)
        
        if self._logger is None:
            self._setup_logger()

    def get_logger(self) -> logging.Logger:
        """return standard logging.Logger"""
        return self._logger

    def _setup_logger(self) -> logging.Logger:
        self._logger = logging.getLogger(self.name)
        self._logger.setLevel(logging.INFO)
        
        self._logger.handlers.clear()
        
        # setup handlers...
        if not self._logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(self.formatter)
            
            # File handler with rotation
            # file_handler = RotatingFileHandler(
            #     filename=os.path.join(self.log_root, log_filename),
            #     maxBytes=10*1024*1024, backupCount=180
            # )
            # file_handler.setLevel(logging.INFO)
            # file_handler.setFormatter(formatter)

            time_rotate_handler = TimedRotatingFileHandler(
                filename=self.log_filepath, 
                when="D", #"S" for testing, 
                backupCount=91,
            )
            time_rotate_handler.setLevel(logging.INFO)
            time_rotate_handler.setFormatter(self.formatter)
            
            self._logger.addHandler(console_handler)
            self._logger.addHandler(time_rotate_handler)
        
        return self._logger
    


# global
proj_access_logger = ProjLogger("accesslog").get_logger()
proj_service_logger = ProjLogger("applog").get_logger()

