"""Small shared CSV writer; protect text cells against spreadsheet formulas."""
import csv
from django.http import StreamingHttpResponse


class Echo:
    def write(self, value):
        return value


def csv_response(filename, headings, rows):
    def safe(value):
        if isinstance(value, str) and (value.startswith(("\t", "\r", "\n")) or value.lstrip().startswith(("=", "+", "-", "@"))):
            return "'" + value
        return value

    def stream():
        writer = csv.writer(Echo())
        yield writer.writerow(headings)
        for row in rows:
            yield writer.writerow([safe(value) for value in row])

    response = StreamingHttpResponse(stream(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
    response["Cache-Control"] = "no-store"
    return response
