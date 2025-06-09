import logging
import sys
from typing import Dict, Any
import json
from datetime import datetime
from app.core.config import settings


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
            
        return json.dumps(log_entry)


def setup_logging():
    root_logger = logging.getLogger()
    
    if root_logger.handlers:
        return
    
    handler = logging.StreamHandler(sys.stdout)
    
    # Use JSON formatter in production, regular formatter in development
    if settings.ENVIRONMENT == "production" or not sys.stdout.isatty():
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Set log level from configuration
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Reduce noise from other libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)