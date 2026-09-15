import json
import logging
import sys
from datetime import datetime
from contextlib import contextmanager

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcfromtimestamp(record.created).isoformat() + 'Z',
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage(),
        }
        
        if hasattr(record, 'extra_fields'):
            for k, v in record.extra_fields.items():
                log_data[k] = v
                
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)

def mask(value: str) -> str:
    if not value:
        return value
    if len(value) <= 8:
        return "***"
    return value[:4] + "***" + value[-4:]

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

@contextmanager
def log_context(logger: logging.Logger, **kwargs):
    adapter = logging.LoggerAdapter(logger, {'extra_fields': kwargs})
    yield adapter
