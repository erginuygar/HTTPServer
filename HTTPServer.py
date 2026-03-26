import socket as s
import threading as t
from datetime import datetime
import json

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
        """Handle individual client connections with keep-alive support"""
        print(f"Handling client {addr}")
        
        try:
            # Set socket timeout to prevent hanging connections
            client_socket.settimeout(5)  # 5 second timeout for keep-alive
            request_count = 0
            
            while True:
                try:
                    # Read the request
                    request_data = client_socket.recv(4096)
                    if not request_data:
                        print(f"Client {addr} closed connection")
                        break
                        
                    request = request_data.decode('utf-8', errors='ignore')
                    request_count += 1
                    
                    print(f"\n{'='*50}")
                    print(f"Request #{request_count} from {addr}:")
                    print(request)
                    print(f"{'='*50}")
                    
                    # Parse the request and check for keep-alive
                    method, path, keep_alive = self.parse_request(request)
                    print(f"Parsed: method={method}, path={path}, keep_alive={keep_alive}")
                    
                    if method and path:
                        # Generate response
                        response = self.generate_response(method, path, keep_alive, request_count)
                        print(f"Sending response (length: {len(response)} bytes)")
                        
                        # Log both request and response
                        self.log_request_response(addr, request, response, request_count)
                        
                        # Send response
                        client_socket.sendall(response.encode('utf-8'))
                        print("Response sent successfully")
                        
                        # If client doesn't want to keep the connection, break
                        if not keep_alive:
                            print(f"Client {addr} requested connection close")
                            break
                    else:
                        print("Failed to parse request")
                        break
                        
                except s.timeout:
                    # Timeout occurred, close the connection
                    print(f"Keep-alive timeout for {addr}, closing connection")
                    break
                except BlockingIOError:
                    # No more data available
                    break
                    
        except Exception as e:
            print(f"Error in handle_client: {e}")
            import traceback
            traceback.print_exc()
        finally:
            client_socket.close()
            print(f"Closed connection with {addr} (processed {request_count} requests)")

    def parse_request(self, request):
        """Parse HTTP request to get method, path, and keep-alive status"""
        try:
            lines = request.splitlines()
            if len(lines) == 0:
                return None, None, False
            
            # Parse request line
            request_line = lines[0].strip()
            print(f"Request line: {request_line}")
            parts = request_line.split()
            if len(parts) < 2:
                return None, None, False
            
            method = parts[0]
            path = parts[1]
            
            # Parse headers for Connection field
            keep_alive = False
            http_version = "1.1"
            
            if len(parts) == 3:
                http_version = parts[2].split('/')[1] if '/' in parts[2] else "1.0"
            
            # Check headers for Connection
            for line in lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip().lower()
                    
                    if key == 'connection':
                        if value == 'keep-alive':
                            keep_alive = True
                        elif value == 'close':
                            keep_alive = False
            
            # HTTP/1.1 defaults to keep-alive unless specified otherwise
            if http_version == "1.1" and not any('connection:' in l.lower() for l in lines[1:]):
                keep_alive = True
                
            print(f"HTTP Version: {http_version}, Keep-Alive: {keep_alive}")
            return method, path, keep_alive
            
        except Exception as e:
            print(f"Error parsing request: {e}")
            return None, None, False

    def generate_response(self, method, path, keep_alive, request_count):
        """Generate HTTP response with proper keep-alive headers"""
        print(f"Generating response for {method} {path} (keep_alive={keep_alive})")
        
        # Define variables at the beginning to avoid scope issues
        body = ""
        status = ""
        status_code = 0
        
        if method == 'GET':
            if path == '/':
                # Prepare the dynamic values
                keep_alive_msg = "Keep-Alive" if keep_alive else "Close"
                keep_alive_status = "Enabled" if keep_alive else "Disabled"
                keep_alive_text = "being kept alive" if keep_alive else "closing after this response"
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Build HTML using string concatenation (simpler to avoid scope issues)
                body = '<!DOCTYPE html>\n'
                body += '<html>\n'
                body += '<head>\n'
                body += '    <title>Python HTTP Server with Keep-Alive</title>\n'
                body += '    <style>\n'
                body += '        body { font-family: Arial, sans-serif; margin: 40px; background: #f0f0f0; }\n'
                body += '        .container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }\n'
                body += '        h1 { color: #333; }\n'
                body += '        .info { background: #e8f4f8; padding: 10px; border-radius: 4px; margin: 10px 0; }\n'
                body += '        .timestamp { color: #666; font-size: 12px; }\n'
                body += '        .stats { background: #f8f8e8; padding: 10px; border-radius: 4px; margin: 10px 0; }\n'
                body += '    </style>\n'
                body += '</head>\n'
                body += '<body>\n'
                body += '    <div class="container">\n'
                body += '        <h1>Welcome to the HTTP Server with Keep-Alive!</h1>\n'
                body += '        <div class="info">\n'
                body += '            <p><strong>Server:</strong> Python HTTP Server</p>\n'
                body += '            <p><strong>Connection:</strong> ' + keep_alive_msg + '</p>\n'
                body += '            <p><strong>Request Number:</strong> ' + str(request_count) + '</p>\n'
                body += '            <p><strong>Time:</strong> ' + current_time + '</p>\n'
                body += '        </div>\n'
                body += '        <div class="stats">\n'
                body += '            <p><strong>Request Info:</strong></p>\n'
                body += '            <p>Method: ' + method + '<br>\n'
                body += '            Path: ' + path + '<br>\n'
                body += '            Keep-Alive: ' + keep_alive_status + '</p>\n'
                body += '        </div>\n'
                body += '        <p>This connection is ' + keep_alive_text + '.</p>\n'
                body += '        <p>You can make multiple requests over the same connection!</p>\n'
                body += '    </div>\n'
                body += '</body>\n'
                body += '</html>'
                status = "200 OK"
                status_code = 200
                
            elif path == '/stats':
                # Stats endpoint
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                body = '<!DOCTYPE html>\n'
                body += '<html>\n'
                body += '<head><title>Server Stats</title></head>\n'
                body += '<body>\n'
                body += '    <h1>Server Statistics</h1>\n'
                body += '    <p>This is request #' + str(request_count) + ' on this connection</p>\n'
                body += '    <p>Server Time: ' + current_time + '</p>\n'
                body += '    <p>Method: ' + method + '</p>\n'
                body += '    <p>Path: ' + path + '</p>\n'
                body += '    <p>Keep-Alive: ' + str(keep_alive) + '</p>\n'
                body += '</body>\n'
                body += '</html>'
                status = "200 OK"
                status_code = 200
            else:
                # 404 Not Found
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                body = '<!DOCTYPE html>\n'
                body += '<html>\n'
                body += '<head><title>404 Not Found</title></head>\n'
                body += '<body>\n'
                body += '    <h1>404 Not Found</h1>\n'
                body += '    <p>The requested URL ' + path + ' was not found on this server.</p>\n'
                body += '    <p>Time: ' + current_time + '</p>\n'
                body += '    <hr>\n'
                body += '    <em>Python HTTP Server</em>\n'
                body += '</body>\n'
                body += '</html>'
                status = "404 Not Found"
                status_code = 404
        else:
            # 405 Method Not Allowed
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            body = '<!DOCTYPE html>\n'
            body += '<html>\n'
            body += '<head><title>405 Method Not Allowed</title></head>\n'
            body += '<body>\n'
            body += '    <h1>405 Method Not Allowed</h1>\n'
            body += '    <p>The method ' + method + ' is not allowed for this resource.</p>\n'
            body += '    <p>Time: ' + current_time + '</p>\n'
            body += '    <hr>\n'
            body += '    <em>Python HTTP Server</em>\n'
            body += '</body>\n'
            body += '</html>'
            status = "405 Method Not Allowed"
            status_code = 405
        
        # Build response with proper headers
        response = f"HTTP/1.1 {status}\r\n"
        response += f"Content-Type: text/html\r\n"
        response += f"Content-Length: {len(body)}\r\n"
        
        # Add keep-alive header if needed
        if keep_alive:
            response += f"Connection: keep-alive\r\n"
            response += f"Keep-Alive: timeout=5, max=100\r\n"
        else:
            response += f"Connection: close\r\n"
        
        response += f"Server: Python-HTTP-Server/1.0\r\n"
        response += f"Date: {datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')}\r\n"
        response += f"\r\n"
        response += body
        
        return response
        
    def log_request_response(self, addr, request, response, request_count):
        """Log both request and response to file with detailed information"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Parse status code from response
        status_line = response.splitlines()[0] if response else ""
        status_code = "Unknown"
        if "HTTP/" in status_line:
            parts = status_line.split()
            if len(parts) >= 2:
                status_code = parts[1]
        
        # Parse request line
        request_line = request.splitlines()[0] if request else ""
        
        try:
            # Log to main log file with both request and response
            with open("server.log", "a") as log_file:
                log_file.write(f"\n{'='*80}\n")
                log_file.write(f"TIMESTAMP: {timestamp}\n")
                log_file.write(f"CLIENT: {addr[0]}:{addr[1]}\n")
                log_file.write(f"REQUEST #{request_count}\n")
                log_file.write(f"{'-'*40}\n")
                log_file.write(f"REQUEST:\n{request}\n")
                log_file.write(f"{'-'*40}\n")
                log_file.write(f"RESPONSE:\n{response}\n")
                log_file.write(f"{'-'*40}\n")
                log_file.write(f"STATUS: {status_code}\n")
                log_file.write(f"{'='*80}\n")
            
            # Also log to a structured JSON log for easier analysis
            try:
                with open("server_detailed.log", "a") as json_file:
                    log_entry = {
                        "timestamp": timestamp,
                        "client_ip": addr[0],
                        "client_port": addr[1],
                        "request_number": request_count,
                        "request": {
                            "raw": request[:500],  # Truncate if too long
                            "first_line": request_line
                        },
                        "response": {
                            "status_code": status_code,
                            "first_line": status_line,
                            "raw": response[:500]  # Truncate if too long
                        }
                    }
                    json_file.write(json.dumps(log_entry) + "\n")
            except Exception as e:
                print(f"Error writing JSON log: {e}")
            
            print(f"Logged request #{request_count} and response to server.log")
            
            # Create summary log for quick overview
            with open("server_summary.log", "a") as summary_file:
                summary_file.write(f"{timestamp} | {addr[0]}:{addr[1]} | #{request_count} | {request_line} | Status: {status_code}\n")
            
        except Exception as e:
            print(f"Error logging request/response: {e}")
    
    def start(self):
        """Start the server and accept connections"""
        print(f"\n{'='*60}")
        print(f"Server listening on {self.host}:{self.port}")
        print(f"Keep-Alive: Enabled (5 second timeout)")
        print(f"Maximum requests per connection: 100")
        print(f"{'='*60}")
        print("\nLogging Information:")
        print(f"  - server.log: Complete request and response logs")
        print(f"  - server_summary.log: Summary of all requests")
        print(f"  - server_detailed.log: JSON formatted logs for analysis")
        print(f"\n{'='*60}\n")
        print("Waiting for connections...")
        
        while True:
            try:
                client_socket, addr = self.server_socket.accept()
                print(f"\n[+] Accepted connection from {addr}")
                
                client_thread = t.Thread(target=self.handle_client, args=(client_socket, addr))
                client_thread.daemon = True
                client_thread.start()
                print(f"[+] Started thread for {addr}")
                
            except KeyboardInterrupt:
                print("\n\n[!] Shutting down server...")
                break
            except Exception as e:
                print(f"[!] Error accepting connection: {e}")
        
        self.server_socket.close()
        print("[!] Server stopped")

def main():
    server = HTTPServer(SERVER_HOST, SERVER_PORT)
    server.start()

if __name__ == "__main__":
    main()