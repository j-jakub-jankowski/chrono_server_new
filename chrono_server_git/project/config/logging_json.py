import json
import logging


class JsonFormatter(logging.Formatter):

    def format(self, record):
        data = {
            key: getattr(record, key)
            for key in record.__dict__
            if not key.startswith("_")
            and key
            not in (
                "args",
                "msg",
                "exc_info",
                "exc_text",
                "stack_info",
            )
        }

        data["message"] = record.getMessage()

        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)

        return json.dumps(
            data,
            ensure_ascii=False,
            default=str,
        )
