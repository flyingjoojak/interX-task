import logging
import re

_PII_PATTERNS = [
    (re.compile(r"010-\d{4}-\d{4}"), "010-***-****"),
    (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "***@***.***"),
    (re.compile(r"\d{6}-[1-4]\d{6}"), "******-*******"),
]


class _PiiFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for pattern, replacement in _PII_PATTERNS:
            msg = pattern.sub(replacement, msg)
        record.msg = msg
        record.args = ()
        return True


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(handler)
    if not any(isinstance(f, _PiiFilter) for f in logger.filters):
        logger.addFilter(_PiiFilter())
    logger.setLevel(logging.INFO)
    return logger
