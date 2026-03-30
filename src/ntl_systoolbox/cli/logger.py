import logging
import json
from datetime import datetime

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno
        }

        if hasattr(record, "extra_data"):
            log_record.update(record.extra_data)

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record, ensure_ascii=False)


def get_logger(name="app"):
    logger = logging.getLogger(name)

    if not logger.handlers:  # évite les doublons si importé plusieurs fois
        logger.setLevel(logging.INFO)

        handler = logging.FileHandler("logs/log.log", encoding="utf-8")
        handler.setFormatter(JsonFormatter())

        logger.addHandler(handler)

    return logger