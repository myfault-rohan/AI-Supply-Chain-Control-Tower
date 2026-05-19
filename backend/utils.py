"""
Utility functions for FastAPI application.
Includes logging, response formatting, and common helpers.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict
import structlog

# ============================================================================
# Structured Logging Setup
# ============================================================================
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


# ============================================================================
# Response Formatting
# ============================================================================
class APIResponse:
    """Standardized API response formatter."""
    
    @staticmethod
    def success(data: Any = None, message: str = "Success") -> Dict:
        """Format successful response."""
        return {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def error(message: str, code: str = "ERROR", status_code: int = 400) -> Dict:
        """Format error response."""
        return {
            "success": False,
            "message": message,
            "code": code,
            "timestamp": datetime.utcnow().isoformat()
        }


# ============================================================================
# File Utilities
# ============================================================================
import re

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks."""
    name = os.path.basename(filename)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    name = name.lstrip('.')
    if not name:
        raise ValueError("Invalid filename after sanitization")
    return name


def validate_file_path(base_dir: str, file_path: str) -> str:
    """Ensure file path stays within base directory."""
    abs_base = os.path.abspath(base_dir)
    abs_path = os.path.abspath(file_path)
    if not abs_path.startswith(abs_base + os.sep):
        raise ValueError("Invalid file path: outside base directory")
    return abs_path
