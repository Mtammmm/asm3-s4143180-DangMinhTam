import json

from .errors import ApiError


# Leave room for headers, metadata, and the Lambda proxy's JSON envelope.
MAX_RESPONSE_ROW_BYTES = 1024 * 1024
MAX_RESPONSE_ROWS = 100


class ResponseRows:
    """Collect complete rows without exceeding the display response budget."""

    def __init__(self):
        self.rows = []
        self.size = 2  # JSON array brackets.

    def append(self, row):
        if len(self.rows) == MAX_RESPONSE_ROWS:
            return False
        row_size = len(json.dumps(row, ensure_ascii=True).encode("utf-8")) + 2
        if self.size + row_size > MAX_RESPONSE_ROW_BYTES:
            if not self.rows:
                raise ApiError(
                    "A dataset row is too large to display. Upload a CSV with smaller rows.",
                    413, "ROW_TOO_LARGE",
                )
            return False
        self.rows.append(row)
        self.size += row_size
        return True


def bounded_response_rows(rows):
    selected = ResponseRows()
    for row in rows:
        if not selected.append(row):
            break
    return selected.rows
