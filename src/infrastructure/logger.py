import json
from logging import LogRecord, getLogger, StreamHandler, Formatter, INFO


class JsonFormatter(Formatter):
    def format(self, record: LogRecord) -> str:
        try:
            data = record.__dict__.copy()
            # data = vars(record)
            exc_info = data.pop("exc_info")
            if exc_info:
                data["traceback"] = self.formatException(exc_info).splitlines()
            return json.dumps(data)
        except Exception:
            return super().format(record)


handler = StreamHandler()
handler.setFormatter(JsonFormatter())

logger = getLogger()
logger.setLevel(INFO)
logger.addHandler(handler)
