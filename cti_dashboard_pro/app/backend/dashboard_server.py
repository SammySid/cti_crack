import json
import os
import tempfile
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from excel_filter_service import generate_filtered_workbook, generate_filtered_workbook_from_directory
from excel_gen import generate_excel_from_payload, sanitize_filename


MAX_PAYLOAD_BYTES = 5 * 1024 * 1024
MAX_MULTIPART_BYTES = 100 * 1024 * 1024


class DashboardHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/export-excel':
            self._handle_export_excel()
            return
        if parsed.path == '/api/filter-excel':
            self._handle_filter_excel()
            return
        if parsed.path == '/api/filter-excel-local':
            self._handle_filter_excel_local()
            return
        self.send_error(404, 'Not Found')

    def _handle_export_excel(self):
        try:
            content_length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            content_length = 0

        if content_length <= 0:
            self._send_json_error(400, 'Missing request body.')
            return
        if content_length > MAX_PAYLOAD_BYTES:
            self._send_json_error(413, 'Payload too large.')
            return

        try:
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body.decode('utf-8'))
        except json.JSONDecodeError:
            self._send_json_error(400, 'Invalid JSON payload.')
            return
        except UnicodeDecodeError:
            self._send_json_error(400, 'Request must be UTF-8 JSON.')
            return

        project_name = payload.get('inputs', {}).get('projectName', 'Thermal Analysis')
        safe_name = sanitize_filename(project_name)
        download_name = f'Professional_Report_{safe_name}.xlsx'

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_output = os.path.join(temp_dir, download_name)
                generate_excel_from_payload(payload, temp_output)
                with open(temp_output, 'rb') as file_obj:
                    file_bytes = file_obj.read()
        except Exception as exc:
            self._send_json_error(400, f'Failed to generate report: {exc}')
            return

        self._send_xlsx(download_name, file_bytes)

    def _handle_filter_excel(self):
        try:
            content_length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            content_length = 0

        if content_length <= 0:
            self._send_json_error(400, 'Missing request body.')
            return
        if content_length > MAX_MULTIPART_BYTES:
            self._send_json_error(413, 'Upload too large.')
            return

        content_type = self.headers.get('Content-Type', '')
        if 'multipart/form-data' not in content_type:
            self._send_json_error(400, 'Content-Type must be multipart/form-data.')
            return

        boundary = self._extract_boundary(content_type)
        if not boundary:
            self._send_json_error(400, 'Multipart boundary is missing.')
            return

        raw_body = self.rfile.read(content_length)
        form = self._parse_multipart_form(raw_body, boundary)

        start_time = (form.get('fields', {}).get('startTime') or [''])[0]
        end_time = (form.get('fields', {}).get('endTime') or [''])[0]
        if not start_time or not end_time:
            self._send_json_error(400, 'Both start and end times are required.')
            return

        file_fields = form.get('files', {}).get('files', [])
        if not file_fields:
            self._send_json_error(400, 'Please upload at least one Excel file.')
            return

        file_items = []
        for field in file_fields:
            file_name = os.path.basename(field.get('filename', '') or '')
            if not file_name.lower().endswith('.xlsx'):
                continue
            file_bytes = field.get('content', b'')
            if file_bytes:
                file_items.append((file_name, file_bytes))

        if not file_items:
            self._send_json_error(400, 'Please upload valid .xlsx files.')
            return

        try:
            download_name, file_bytes = generate_filtered_workbook(file_items, start_time, end_time)
        except Exception as exc:
            self._send_json_error(400, f'Failed to filter files: {exc}')
            return

        self._send_xlsx(download_name, file_bytes)

    def _handle_filter_excel_local(self):
        try:
            content_length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            content_length = 0

        if content_length <= 0:
            self._send_json_error(400, 'Missing request body.')
            return
        if content_length > MAX_PAYLOAD_BYTES:
            self._send_json_error(413, 'Payload too large.')
            return

        try:
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body.decode('utf-8'))
        except json.JSONDecodeError:
            self._send_json_error(400, 'Invalid JSON payload.')
            return
        except UnicodeDecodeError:
            self._send_json_error(400, 'Request must be UTF-8 JSON.')
            return

        start_time = str(payload.get('startTime', '')).strip()
        end_time = str(payload.get('endTime', '')).strip()
        source_path = str(payload.get('sourcePath', '')).strip()
        if not start_time or not end_time or not source_path:
            self._send_json_error(400, 'startTime, endTime and sourcePath are required.')
            return

        try:
            download_name, file_bytes = generate_filtered_workbook_from_directory(source_path, start_time, end_time)
        except Exception as exc:
            self._send_json_error(400, f'Failed to filter files: {exc}')
            return

        self._send_xlsx(download_name, file_bytes)

    def _send_xlsx(self, file_name, file_bytes):
        self.send_response(200)
        self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.send_header('Content-Disposition', f'attachment; filename="{file_name}"')
        self.send_header('Content-Length', str(len(file_bytes)))
        self.end_headers()
        self.wfile.write(file_bytes)

    def _send_json_error(self, status_code, message):
        response = json.dumps({'error': message}).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def _extract_boundary(self, content_type):
        for token in content_type.split(';'):
            token = token.strip()
            if token.startswith('boundary='):
                boundary = token.split('=', 1)[1].strip('"')
                return boundary.encode('utf-8')
        return None

    def _parse_content_disposition(self, value):
        result = {}
        for part in value.split(';'):
            part = part.strip()
            if '=' in part:
                key, val = part.split('=', 1)
                result[key.strip().lower()] = val.strip().strip('"')
        return result

    def _parse_multipart_form(self, body, boundary):
        delimiter = b'--' + boundary
        segments = body.split(delimiter)
        fields = {}
        files = {}

        for segment in segments[1:]:
            if segment in (b'', b'--\r\n', b'--'):
                continue

            segment = segment.lstrip(b'\r\n')
            if segment.endswith(b'--\r\n'):
                segment = segment[:-4]
            elif segment.endswith(b'--'):
                segment = segment[:-2]
            if segment.endswith(b'\r\n'):
                segment = segment[:-2]

            header_blob, sep, content = segment.partition(b'\r\n\r\n')
            if not sep:
                continue

            headers = {}
            for line in header_blob.decode('utf-8', errors='replace').split('\r\n'):
                if ':' in line:
                    k, v = line.split(':', 1)
                    headers[k.strip().lower()] = v.strip()

            disposition = headers.get('content-disposition', '')
            attrs = self._parse_content_disposition(disposition)
            name = attrs.get('name')
            filename = attrs.get('filename')
            if not name:
                continue

            if filename:
                files.setdefault(name, []).append({
                    'filename': filename,
                    'content': content
                })
            else:
                fields.setdefault(name, []).append(content.decode('utf-8', errors='replace'))

        return {'fields': fields, 'files': files}


def run_server(port=8000):
    project_root = Path(__file__).resolve().parents[2]
    web_root = project_root / 'app' / 'web'
    if not web_root.exists():
        raise FileNotFoundError(f'Web root not found: {web_root}')

    handler = partial(DashboardHandler, directory=str(web_root))
    server = ThreadingHTTPServer(('0.0.0.0', port), handler)
    print(f'Dashboard server running on http://localhost:{port}')
    print(f'Serving static files from: {web_root}')
    print('Press Ctrl+C to stop the server.')
    server.serve_forever()


if __name__ == '__main__':
    run_server()
