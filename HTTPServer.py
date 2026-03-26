import socket as s
import threading as t
from datetime import datetime
import os

SERVER_HOST = '0.0.0.0'
SERVER_PORT = 8000

class HTTPServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = s.socket(s.AF_INET, s.SOCK_STREAM)
        self.server_socket.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"HTTP Server running on {self.host}:{self.port}")

    def handle_client(self, client_socket, addr):
        """Handle individual client connections"""
        try:
            while True:
                # Read request with proper buffer handling
                request_data = b""
                while True:
                    chunk = client_socket.recv(4096)
                    if not chunk:
                        return
                    request_data += chunk
                    if b"\r\n\r\n" in request_data:
                        break
                
                request = request_data.decode('utf-8', errors='ignore')
                print(f"Received request from {addr}:\n{request[:500]}...")
                
                # Parse request
                method, path, headers, keep_alive = self.parse_request(request)
                
                if not method:
                    break
                
                # Log the request
                self.log_request(addr, method, path, headers)
                
                # Generate and send response
                response = self.generate_response(method, path, headers)
                client_socket.sendall(response.encode())
                
                # Check if connection should be closed
                if not keep_alive:
                    break
                    
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            client_socket.close()
            print(f"Connection closed with {addr}")

    def parse_request(self, request):
        """Parse HTTP request and extract relevant information"""
        lines = request.splitlines()
        if len(lines) == 0:
            return None, None, None, False
        
        # Parse request line
        request_line = lines[0].strip()
        parts = request_line.split()
        if len(parts) != 3:
            return None, None, None, False
        
        method, path, version = parts
        
        # Parse headers
        headers = {}
        keep_alive = False
        content_length = 0
        
        for line in lines[1:]:
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip()] = value.strip()
        
        # Check for Keep-Alive
        if headers.get('Connection', '').lower() == 'keep-alive':
            keep_alive = True
        
        return method, path, headers, keep_alive

    def generate_response(self, method, path, headers):
        """Generate appropriate HTTP response"""
        
        # Handle different HTTP methods
        if method == 'GET':
            return self.handle_get(path)
        elif method == 'HEAD':
            return self.handle_head(path)
        elif method == 'POST':
            return self.handle_post(path, headers)
        else:
            return self.error_response(405, "Method Not Allowed")

    def handle_get(self, path):
        """Handle GET requests"""
        if path == '/':
            body = """<!DOCTYPE html>
<html>
<head>
    <title>Python HTTP Server</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        .info { background: #f0f0f0; padding: 20px; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>Welcome to the Python HTTP Server!</h1>
    <div class="info">
        <p>Server is running successfully.</p>
        <p>Current time: {}</p>
    </div>
</body>
</html>""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return self.create_response(200, "OK", "text/html", body)
        elif path == '/status':
            body = f"Server Status: Running\nUptime: {datetime.now()}"
            return self.create_response(200, "OK", "text/plain", body)
        elif path.startswith('/echo/'):
            message = path[6:]
            return self.create_response(200, "OK", "text/plain", message)
        else:
            return self.error_response(404, "Not Found")

    def handle_head(self, path):
        """Handle HEAD requests (same as GET but without body)"""
        response = self.handle_get(path)
        # Remove the body for HEAD response
        lines = response.split('\r\n')
        headers = []
        body_started = False
        for line in lines:
            if not body_started:
                headers.append(line)
                if line == '':
                    body_started = True
        return '\r\n'.join(headers)

    def handle_post(self, path, headers):
        """Handle POST requests"""
        if path == '/':
            body = "POST request received successfully"
            return self.create_response(200, "OK", "text/plain", body)
        else:
            return self.error_response(404, "Not Found")

    def create_response(self, status_code, status_text, content_type, body):
        """Create HTTP response with proper headers"""
        response = f"HTTP/1.1 {status_code} {status_text}\r\n"
        response += f"Content-Type: {content_type}\r\n"
        response += f"Content-Length: {len(body)}\r\n"
        response += "Connection: keep-alive\r\n"
        response += f"Server: Python-HTTP-Server/1.0\r\n"
        response += f"Date: {datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')}\r\n"
        response += "\r\n"
        response += body
        return response

    def error_response(self, status_code, status_text):
        """Generate error response"""
        body = f"""<!DOCTYPE html>
<html>
<head><title>{status_code} {status_text}</title></head>
<body>
    <h1>{status_code} {status_text}</h1>
    <p>The requested resource could not be found or method is not allowed.</p>
    <hr>
    <em>Python HTTP Server</em>
</body>
</html>"""
        content_type = "text/html"
        response = f"HTTP/1.1 {status_code} {status_text}\r\n"
        response += f"Content-Type: {content_type}\r\n"
        response += f"Content-Length: {len(body)}\r\n"
        response += "Connection: close\r\n"
        response += "\r\n"
        response += body
        return response
        
    def log_request(self, addr, method, path, headers):
        """Log request details to file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} - {addr[0]}:{addr[1]} - {method} {path}\n"
        
        try:
            with open("server.log", "a") as log_file:
                log_file.write(log_entry)
        except Exception as e:
            print(f"Error logging request: {e}")

    def start(self):
        """Start the server and accept connections"""
        print(f"Server starting on {self.host}:{self.port}")
        print("Press Ctrl+C to stop the server")
        
        try:
            while True:
                client_socket, addr = self.server_socket.accept()
                print(f"Accepted connection from {addr}")
                
                # Create a new thread for each client
                client_thread = t.Thread(
                    target=self.handle_client, 
                    args=(client_socket, addr),
                    daemon=True
                )
                client_thread.start()
                
        except KeyboardInterrupt:
            print("\nShutting down server...")
        finally:
            self.server_socket.close()
            print("Server stopped")

def main():
    server = HTTPServer(SERVER_HOST, SERVER_PORT)
    server.start()

if __name__ == "__main__":
    main()