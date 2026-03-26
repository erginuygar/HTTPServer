import socket as s
import threading as t
from datetime import datetime
import os
import mimetypes
import time
from urllib.parse import unquote

SERVER_HOST = '0.0.0.0'
SERVER_PORT = 8000
WEB_ROOT = 'www'  # Directory for web files

class WebServer:
    def __init__(self, host, port, root='www'):
        self.host = host
        self.port = port
        self.root = root
        self.server_socket = s.socket(s.AF_INET, s.SOCK_STREAM)
        self.server_socket.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        
        # Create web root directory if it doesn't exist
        if not os.path.exists(self.root):
            os.makedirs(self.root)
            self.create_sample_files()
            
        print(f"Web Server running on {self.host}:{self.port}")
        print(f"Serving files from: {os.path.abspath(self.root)}")

    def create_sample_files(self):
        """Create sample files for testing"""
        # Create sample HTML file
        with open(os.path.join(self.root, 'index.html'), 'w') as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Welcome to Python Web Server</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f0f0f0; }
        .container { background: white; padding: 20px; border-radius: 8px; }
        h1 { color: #333; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome to the Python Web Server!</h1>
        <p>This is a multi-threaded web server supporting:</p>
        <ul>
            <li>GET and HEAD methods</li>
            <li>Persistent and non-persistent connections</li>
            <li>Last-Modified and If-Modified-Since headers</li>
            <li>Multiple response status codes</li>
        </ul>
        <p><a href="/test.txt">Test Text File</a></p>
        <p><a href="/sample.jpg">Sample Image</a></p>
    </div>
</body>
</html>""")
        
        # Create sample text file
        with open(os.path.join(self.root, 'test.txt'), 'w') as f:
            f.write("This is a test text file.\nCreated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # Create sample image file (simple 1x1 pixel JPEG)
        with open(os.path.join(self.root, 'sample.jpg'), 'wb') as f:
            # Minimal valid JPEG
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x03\x02\x02\x02\x02\x02\x03\x02\x02\x02\x03\x03\x03\x03\x04\x06\x04\x04\x04\x04\x04\x08\x06\x06\x05\x06\t\x08\n\n\x08\t\n\x0c\x10\x0c\x0c\x0c\x0c\x0c\x18\x0f\x12\x15\x14\x11\x0f\x12\x1a\x16\x12\x13\x13\x15\x1c\x1a\x1d\x1d\x1d\x1c\x1a\x1c\x1d\x1e\x1f!%&$# \x1f\x1f#&\'\"\x1f\x1f\x1f\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\x00\x00\x00\xff\xd9')
        
        # Create a file with future date for testing 304
        future_time = time.time() + 86400  # 1 day in future
        future_file = os.path.join(self.root, 'future.txt')
        with open(future_file, 'w') as f:
            f.write("This file has a future modification date for testing.")
        os.utime(future_file, (future_time, future_time))

    def handle_client(self, client_socket, addr):
        """Handle individual client connections"""
        print(f"\n[+] Connection from {addr}")
        
        try:
            client_socket.settimeout(5)
            request_count = 0
            
            while True:
                try:
                    # Read request
                    request_data = client_socket.recv(4096)
                    if not request_data:
                        break
                    
                    request = request_data.decode('utf-8', errors='ignore')
                    request_count += 1
                    
                    print(f"\n--- Request #{request_count} from {addr} ---")
                    print(request.split('\n')[0])  # Print first line only
                    
                    # Parse request
                    method, path, headers, keep_alive = self.parse_request(request)
                    
                    if not method:
                        response = self.generate_error_response(400, "Bad Request", keep_alive)
                        self.send_response(client_socket, response)
                        break
                    
                    # Log request
                    self.log_request(addr, method, path, headers)
                    
                    # Generate response
                    response = self.process_request(method, path, headers, keep_alive)
                    
                    # Send response
                    self.send_response(client_socket, response)
                    
                    # Break if connection should close
                    if not keep_alive:
                        print(f"[-] Closing connection with {addr} (non-persistent)")
                        break
                    
                except s.timeout:
                    print(f"[-] Timeout for {addr}")
                    break
                except Exception as e:
                    print(f"[!] Error: {e}")
                    import traceback
                    traceback.print_exc()
                    break
                    
        except Exception as e:
            print(f"[!] Client error: {e}")
        finally:
            client_socket.close()
            print(f"[-] Closed connection with {addr} (processed {request_count} requests)")

    def send_response(self, client_socket, response):
        """Send response (handles both string and bytes)"""
        if isinstance(response, str):
            client_socket.sendall(response.encode('utf-8'))
        else:
            client_socket.sendall(response)

    def parse_request(self, request):
        """Parse HTTP request"""
        try:
            lines = request.splitlines()
            if len(lines) == 0:
                return None, None, None, False
            
            # Parse request line
            request_line = lines[0].strip()
            parts = request_line.split()
            if len(parts) < 2:
                return None, None, None, False
            
            method = parts[0].upper()
            path = unquote(parts[1])  # URL decode
            version = parts[2] if len(parts) == 3 else "HTTP/1.1"
            
            # Parse headers
            headers = {}
            keep_alive = False
            
            for line in lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
            
            # Determine keep-alive
            if version == "HTTP/1.1":
                # HTTP/1.1 defaults to persistent
                keep_alive = headers.get('connection', '').lower() != 'close'
            else:
                # HTTP/1.0 defaults to non-persistent
                keep_alive = headers.get('connection', '').lower() == 'keep-alive'
            
            return method, path, headers, keep_alive
            
        except Exception as e:
            print(f"Parse error: {e}")
            return None, None, None, False

    def process_request(self, method, path, headers, keep_alive):
        """Process HTTP request and generate response"""
        
        # Security: Prevent directory traversal
        safe_path = os.path.normpath(path).lstrip('/')
        if '..' in path or safe_path.startswith('..'):
            return self.generate_error_response(403, "Forbidden", keep_alive)
        
        # Handle root path
        if path == '/' or path == '':
            safe_path = 'index.html'
        
        file_path = os.path.join(self.root, safe_path)
        
        # Check if file exists
        if not os.path.exists(file_path):
            return self.generate_error_response(404, "File Not Found", keep_alive)
        
        # Check if it's a file (not directory)
        if os.path.isdir(file_path):
            return self.generate_error_response(403, "Forbidden", keep_alive)
        
        # Check if method is allowed
        if method not in ['GET', 'HEAD']:
            return self.generate_error_response(405, "Method Not Allowed", keep_alive)
        
        # Get file stats
        file_stat = os.stat(file_path)
        last_modified = datetime.fromtimestamp(file_stat.st_mtime)
        content_length = file_stat.st_size
        
        # Determine MIME type
        content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
        
        # Check If-Modified-Since header for 304 response
        if 'if-modified-since' in headers:
            try:
                # Parse If-Modified-Since header
                ims_str = headers['if-modified-since']
                # Handle different date formats
                try:
                    ims_time = datetime.strptime(ims_str, '%a, %d %b %Y %H:%M:%S %Z')
                except:
                    ims_time = datetime.strptime(ims_str, '%a, %d %b %Y %H:%M:%S')
                
                # If file hasn't been modified, return 304
                if last_modified <= ims_time:
                    return self.generate_304_response(keep_alive)
            except Exception as e:
                print(f"Error parsing If-Modified-Since: {e}")
        
        # Read file content
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return self.generate_error_response(403, "Forbidden", keep_alive)
        
        # Generate response
        response = self.generate_response(
            status_code=200,
            status_text="OK",
            headers={
                'Content-Type': content_type,
                'Content-Length': str(content_length),
                'Last-Modified': last_modified.strftime('%a, %d %b %Y %H:%M:%S GMT'),
                'Cache-Control': 'no-cache'
            },
            body=file_content if method == 'GET' else None,
            keep_alive=keep_alive
        )
        
        return response

    def generate_response(self, status_code, status_text, headers, body=None, keep_alive=True):
        """Generate HTTP response (handles both text and binary)"""
        
        # Build the header section as string
        header_section = f"HTTP/1.1 {status_code} {status_text}\r\n"
        
        # Add headers
        for key, value in headers.items():
            header_section += f"{key}: {value}\r\n"
        
        # Add connection header
        if keep_alive:
            header_section += f"Connection: keep-alive\r\n"
            header_section += f"Keep-Alive: timeout=5, max=100\r\n"
        else:
            header_section += f"Connection: close\r\n"
        
        header_section += f"Server: Python-Web-Server/1.0\r\n"
        header_section += f"Date: {datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')}\r\n"
        header_section += f"\r\n"
        
        # Combine headers and body
        if body is None:
            # HEAD request or no body
            return header_section
        elif isinstance(body, bytes):
            # Binary body (images, etc.)
            return header_section.encode() + body
        else:
            # Text body
            return header_section + body

    def generate_error_response(self, status_code, status_text, keep_alive):
        """Generate error response with HTML body"""
        error_pages = {
            400: "Bad Request - Malformed request syntax",
            403: "Forbidden - Access denied",
            404: "File Not Found",
            405: "Method Not Allowed"
        }
        
        error_message = error_pages.get(status_code, status_text)
        
        body = f"""<!DOCTYPE html>
<html>
<head><title>{status_code} {status_text}</title></head>
<body>
    <h1>{status_code} {status_text}</h1>
    <p>{error_message}</p>
    <hr>
    <em>Python Web Server</em>
</body>
</html>"""
        
        headers = {
            'Content-Type': 'text/html',
            'Content-Length': str(len(body))
        }
        
        return self.generate_response(status_code, status_text, headers, body, keep_alive)

    def generate_304_response(self, keep_alive):
        """Generate 304 Not Modified response"""
        response = f"HTTP/1.1 304 Not Modified\r\n"
        
        if keep_alive:
            response += f"Connection: keep-alive\r\n"
        else:
            response += f"Connection: close\r\n"
        
        response += f"Server: Python-Web-Server/1.0\r\n"
        response += f"Date: {datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')}\r\n"
        response += f"\r\n"
        
        return response

    def log_request(self, addr, method, path, headers):
        """Log request to file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            with open("server.log", "a") as log_file:
                log_file.write(f"\n{'='*80}\n")
                log_file.write(f"TIMESTAMP: {timestamp}\n")
                log_file.write(f"CLIENT: {addr[0]}:{addr[1]}\n")
                log_file.write(f"METHOD: {method}\n")
                log_file.write(f"PATH: {path}\n")
                log_file.write(f"HEADERS:\n")
                for key, value in headers.items():
                    log_file.write(f"  {key}: {value}\n")
                log_file.write(f"{'='*80}\n")
        except Exception as e:
            print(f"Error logging: {e}")

    def start(self):
        """Start the server"""
        print(f"\n{'='*70}")
        print(f"Web Server Configuration:")
        print(f"  Host: {self.host}")
        print(f"  Port: {self.port}")
        print(f"  Root: {os.path.abspath(self.root)}")
        print(f"  Threads: Multi-threaded")
        print(f"  Methods: GET, HEAD")
        print(f"  Connection: Persistent (keep-alive) and Non-persistent")
        print(f"{'='*70}\n")
        print("Server started. Press Ctrl+C to stop.\n")
        
        try:
            while True:
                client_socket, addr = self.server_socket.accept()
                client_thread = t.Thread(target=self.handle_client, args=(client_socket, addr))
                client_thread.daemon = True
                client_thread.start()
                print(f"[+] Thread started for {addr}")
                
        except KeyboardInterrupt:
            print("\n\n[!] Shutting down server...")
        finally:
            self.server_socket.close()
            print("[!] Server stopped")

def main():
    server = WebServer(SERVER_HOST, SERVER_PORT, WEB_ROOT)
    server.start()

if __name__ == "__main__":
    main()