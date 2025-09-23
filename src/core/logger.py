import structlog
import logging
import sys
from typing import Any, Dict
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored output
init(autoreset=True)

class ColoredRenderer:
    """Custom renderer for colored console output."""
    
    def __init__(self):
        self.colors = {
            'debug': Fore.CYAN,
            'info': Fore.GREEN,
            'warning': Fore.YELLOW,
            'error': Fore.RED,
            'critical': Fore.MAGENTA
        }
    
    def __call__(self, logger, method_name: str, event_dict: Dict[str, Any]) -> str:
        level = event_dict.get('level', 'info').lower()
        color = self.colors.get(level, '')
        
        timestamp = event_dict.get('timestamp', '')
        event = event_dict.get('event', '')
        
        # Format the log message
        message = f"{color}[{timestamp}] {level.upper()}: {event}{Style.RESET_ALL}"
        
        # Add extra fields
        extras = {k: v for k, v in event_dict.items() 
                 if k not in ['timestamp', 'level', 'event']}
        
        if extras:
            extra_str = ' | '.join([f"{k}={v}" for k, v in extras.items()])
            message += f" | {extra_str}"
        
        return message

def setup_logging(log_level: str = "INFO") -> structlog.BoundLogger:
    """Setup structured logging with colored output."""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            ColoredRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger()

# Global logger instance
logger = setup_logging()