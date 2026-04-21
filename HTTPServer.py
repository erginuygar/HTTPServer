#!/usr/bin/env python3
"""
Multi-threaded HTTP/1.1 Web Server
COMP2322 Computer Networking Project

A compliant web server that supports:
- GET and HEAD methods for text, HTML, and image files
- Persistent (keep-alive) and non-persistent (close) connections
- Status codes: 200, 400, 403, 404, 304
- Conditional requests with Last-Modified / If-Modified-Since
- Thread‑per‑client concurrency model
- Detailed logging of all requests

Usage:
    python webserver.py

The server listens on 0.0.0.0:8080 and serves files from the 'www' directory.
"""

import socket as s
import threading as t
from datetime import datetime
import os
import mimetypes
import time
from urllib.parse import unquote
import email.utils
import struct

SERVER_HOST = '0.0.0.0'
SERVER_PORT = 8080
WEB_ROOT = 'www'


class WebServer:
    """
    A multi‑threaded HTTP/1.1 web server.
    Each client connection is handled in a separate thread.
    """

    def __init__(self, host, port, root='www'):
        """
        _summary_: Initialise the web server, create listening socket,
                   set up document root, and create sample files if needed.

        _param_: host (str): IP address to bind to (use '0.0.0.0' for all interfaces).
        _param_: port (int): TCP port number (e.g., 8080).
        _param_: root (str): Relative or absolute path to the document root.
        _return_: None
        """
        self.host = host
        self.port = port
        self.root = os.path.abspath(root)

        self.server_socket = s.socket(s.AF_INET, s.SOCK_STREAM)
        self.server_socket.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)

        if not os.path.exists(self.root):
            os.makedirs(self.root)
            self._create_sample_files()

        with open("server.log", "w") as f:
            f.write(f"Server started at {datetime.now()}\n\n")

        print(f"\n{'='*70}")
        print(f"Web Server Configuration:")
        print(f"  Host: {self.host}")
        print(f"  Port: {self.port}")
        print(f"  Root: {self.root}")
        print(f"{'='*70}\n")

    def _create_sample_files(self):
        """
        _summary_: Create default HTML, text, and a future‑dated file for testing.
                   Called only when the web root directory is empty.
                   Does not create any image files; users must supply their own.

        _param_: None
        _return_: None
        """
        with open(os.path.join(self.root, 'index.html'), 'w') as f:
            f.write("""<!DOCTYPE html>
<html><head><title>Python Web Server</title></head>
<body><h1>Multi-Threaded Web Server</h1></body>
</html>""")
        with open(os.path.join(self.root, 'test.txt'), 'w') as f:
            f.write("This is a test text file.\nCreated: " +
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        future_time = time.time() + 86400 * 365
        with open(os.path.join(self.root, 'future.txt'), 'w') as f:
            f.write("This file has a future modification date.")
        os.utime(os.path.join(self.root, 'future.txt'), (future_time, future_time))
        print(f"Sample files created in {self.root}")

    def handle_client(self, client_socket, addr):
        """
        _summary_: Handle a single client connection (may be persistent).
                   Runs in its own thread. Reads HTTP requests repeatedly
                   until the client closes or the server decides to close.

        _param_: client_socket (socket): The connected client socket.
        _param_: addr (tuple): Client address (ip, port).
        _return_: None
        """
        print(f"\n[+] Connection from {addr[0]}:{addr[1]}")
        try:
            client_socket.settimeout(5)
            while True:
                try:
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    request = data.decode('utf-8', errors='ignore')
                    method, path, headers, keep_alive = self._parse_request(request)

                    if method is None:
                        response = self._error_response(400, "Bad Request", keep_alive)
                        self._send_response(client_socket, response)
                        client_socket.setsockopt(s.SOL_SOCKET, s.SO_LINGER,
                                                 struct.pack('ii', 1, 0))
                        client_socket.close()
                        return

                    self._log(addr, method, path, headers)
                    response = self._process_request(method, path, headers, keep_alive)
                    self._send_response(client_socket, response)

                    if not keep_alive:
                        print(f"  Closing connection (non-persistent)")
                        client_socket.setsockopt(s.SOL_SOCKET, s.SO_LINGER,
                                                 struct.pack('ii', 1, 0))
                        client_socket.close()
                        return
                except s.timeout:
                    break
                except Exception as e:
                    print(f"  Error: {e}")
                    break
        finally:
            client_socket.close()
            print(f"[-] Connection closed from {addr[0]}:{addr[1]}")

    def _parse_request(self, request):
        """
        _summary_: Parse an HTTP request string into its components.

        _param_: request (str): Raw HTTP request.
        _return_: tuple: (method, path, headers_dict, keep_alive_flag)
                 If the request is malformed, returns (None, None, None, False).
        """
        try:
            lines = request.splitlines()
            if not lines:
                return None, None, None, False
            request_line = lines[0].strip()
            parts = request_line.split()
            if len(parts) != 3:
                return None, None, None, False
            method = parts[0].upper()
            path = unquote(parts[1])
            version = parts[2]
            if not version.startswith('HTTP/'):
                return None, None, None, False

            headers = {}
            for line in lines[1:]:
                if ':' in line:
                    k, v = line.split(':', 1)
                    headers[k.strip().lower()] = v.strip()

            conn = headers.get('connection', '').lower()
            if version == "HTTP/1.1":
                keep_alive = conn != 'close'
            else:
                keep_alive = conn == 'keep-alive'
            return method, path, headers, keep_alive
        except Exception:
            return None, None, None, False

    def _process_request(self, method, path, headers, keep_alive):
        """
        _summary_: Process a validated HTTP request and generate the appropriate response.

        _param_: method (str): 'GET' or 'HEAD'.
        _param_: path (str): Requested URL path (already URL‑decoded).
        _param_: headers (dict): Request headers (keys in lower case).
        _param_: keep_alive (bool): Whether the connection should stay open.
        _return_: str or bytes: The complete HTTP response (headers + optional body).
        """
        if '..' in path or path.startswith('/..'):
            return self._error_response(403, "Forbidden", keep_alive)

        if path == '/' or path == '':
            rel_path = 'index.html'
        else:
            rel_path = path.lstrip('/')
        file_path = os.path.normpath(os.path.join(self.root, rel_path))
        if not file_path.startswith(self.root):
            return self._error_response(403, "Forbidden", keep_alive)

        if not os.path.exists(file_path):
            return self._error_response(404, "File Not Found", keep_alive)
        if os.path.isdir(file_path):
            return self._error_response(403, "Forbidden", keep_alive)

        if method not in ('GET', 'HEAD'):
            return self._error_response(405, "Method Not Allowed", keep_alive)

        stat = os.stat(file_path)
        last_modified = datetime.fromtimestamp(stat.st_mtime)
        content_length = stat.st_size
        content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

        if 'if-modified-since' in headers:
            try:
                ims_str = headers['if-modified-since']
                ims_tuple = email.utils.parsedate_tz(ims_str)
                if ims_tuple:
                    ims = datetime.fromtimestamp(email.utils.mktime_tz(ims_tuple))
                    if last_modified <= ims:
                        return self._not_modified_response(keep_alive)
            except Exception:
                pass

        body = None
        if method == 'GET':
            with open(file_path, 'rb') as f:
                body = f.read()

        headers_dict = {
            'Content-Type': content_type,
            'Content-Length': str(content_length),
            'Last-Modified': last_modified.strftime('%a, %d %b %Y %H:%M:%S GMT'),
            'Cache-Control': 'no-cache'
        }
        return self._build_response(200, "OK", headers_dict, body, keep_alive)

    def _build_response(self, code, text, headers, body, keep_alive):
        """
        _summary_: Construct a full HTTP response (status line, headers, optional body).

        _param_: code (int): HTTP status code (e.g., 200).
        _param_: text (str): Reason phrase (e.g., 'OK').
        _param_: headers (dict): Response headers (key → value).
        _param_: body (str or bytes or None): Response body (None for HEAD or 304).
        _param_: keep_alive (bool): Whether the connection should stay open.
        _return_: str or bytes: The complete HTTP response.
        """
        resp = f"HTTP/1.1 {code} {text}\r\n"
        for k, v in headers.items():
            resp += f"{k}: {v}\r\n"
        if keep_alive:
            resp += "Connection: keep-alive\r\n"
            resp += "Keep-Alive: timeout=5, max=100\r\n"
        else:
            resp += "Connection: close\r\n"
        resp += f"Server: Python-MultiThread/1.0\r\n"
        resp += f"Date: {datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')}\r\n"
        resp += "\r\n"

        if body is None:
            return resp
        elif isinstance(body, bytes):
            return resp.encode() + body
        else:
            return resp + body

    def _error_response(self, code, text, keep_alive):
        """
        _summary_: Generate an error response with a simple HTML body.

        _param_: code (int): HTTP status code (400, 403, 404, 405).
        _param_: text (str): Reason phrase (e.g., 'Bad Request').
        _param_: keep_alive (bool): Whether the connection should stay open.
        _return_: str: The complete HTTP error response.
        """
        body = f"""<!DOCTYPE html>
<html><head><title>{code} {text}</title></head>
<body><h1>{code} {text}</h1><hr><em>Python Web Server</em></body>
</html>"""
        headers = {'Content-Type': 'text/html', 'Content-Length': str(len(body))}
        return self._build_response(code, text, headers, body, keep_alive)

    def _not_modified_response(self, keep_alive):
        """
        _summary_: Generate a 304 Not Modified response (no body).

        _param_: keep_alive (bool): Whether the connection should stay open.
        _return_: str: The 304 response.
        """
        resp = "HTTP/1.1 304 Not Modified\r\n"
        if keep_alive:
            resp += "Connection: keep-alive\r\n"
        else:
            resp += "Connection: close\r\n"
        resp += f"Server: Python-MultiThread/1.0\r\n"
        resp += f"Date: {datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')}\r\n"
        resp += "\r\n"
        return resp

    def _send_response(self, sock, response):
        """
        _summary_: Send a response (string or bytes) over a socket.

        _param_: sock (socket): The client socket.
        _param_: response (str or bytes): The HTTP response to send.
        _return_: None
        """
        if isinstance(response, str):
            sock.sendall(response.encode())
        else:
            sock.sendall(response)

    def _log(self, addr, method, path, headers):
        """
        _summary_: Log a client request to server.log.

        _param_: addr (tuple): Client (ip, port).
        _param_: method (str): HTTP method.
        _param_: path (str): Requested URL path.
        _param_: headers (dict): Request headers (unused in this simple log).
        _return_: None
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("server.log", "a") as f:
            f.write(f"{timestamp} | {addr[0]}:{addr[1]} | {method} {path}\n")

    def start(self):
        """
        _summary_: Start the web server: accept incoming connections and spawn threads.
                   This method runs the main loop and never returns (until interrupted).

        _param_: None
        _return_: None
        """
        print(f"Server listening on {self.host}:{self.port}")
        print("Press Ctrl+C to stop\n")
        try:
            while True:
                client_sock, addr = self.server_socket.accept()
                t.Thread(target=self.handle_client, args=(client_sock, addr),
                         daemon=True).start()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.server_socket.close()


if __name__ == "__main__":
    server = WebServer(SERVER_HOST, SERVER_PORT, WEB_ROOT)
    server.start()