#!/usr/bin/env python3
"""
COMP2322 Computer Networking - Web Server Tester
Tests all required functionality: GET, HEAD, persistent/non-persistent connections,
status codes (200,400,403,404,304), Last-Modified/If-Modified-Since.
"""

import socket
import sys
import time

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8080

class WebServerTester:
    def __init__(self):
        self.sock = None

    def connect(self):
        self.close()
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((SERVER_HOST, SERVER_PORT))
            self.sock.settimeout(5)
            print(f"✓ Connected to {SERVER_HOST}:{SERVER_PORT}")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            self.sock = None
            return False

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

    def send(self, request):
        if not self.sock:
            print("No connection")
            return None, None
        try:
            print(f"\n[REQUEST]\n{request}")
            self.sock.send(request.encode())
            data = b""
            while True:
                try:
                    chunk = self.sock.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    if len(chunk) < 4096:
                        break
                except socket.timeout:
                    break
            if not data:
                print("No response received")
                return None, None
            response = data.decode('utf-8', errors='ignore')
            lines = response.split('\n')[:15]
            print("\n[RESPONSE]")
            for line in lines:
                print(line)
            if len(response.split('\n')) > 15:
                print("... (truncated)")
            status_line = response.split('\n')[0] if response else ""
            status = status_line.split()[1] if len(status_line.split()) > 1 else "Unknown"
            print(f"\nStatus: {status}")
            return response, status
        except Exception as e:
            print(f"Error: {e}")
            return None, None

    def test_get_text(self):
        print("\n" + "="*60)
        print("TEST 1: GET Text File")
        if not self.connect():
            print("✗ FAILED - cannot connect")
            return False
        req = "GET /test.txt HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
        _, status = self.send(req)
        self.close()
        ok = status == "200"
        print("✓ PASSED" if ok else f"✗ FAILED (got {status})")
        return ok

    def test_get_image(self):
        print("\n" + "="*60)
        print("TEST 2: GET Image File")
        candidates = ['test.jpg', 'sample.jpg', 'image.jpg', 'photo.jpg']
        for img in candidates:
            if not self.connect():
                continue
            req = f"GET /{img} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
            _, status = self.send(req)
            self.close()
            if status == "200":
                print(f"✓ PASSED (found {img})")
                return True
        print("✗ FAILED - no image found in www/")
        return False

    def test_head(self):
        print("\n" + "="*60)
        print("TEST 3: HEAD Request")
        if not self.connect():
            print("✗ FAILED - cannot connect")
            return False
        req = "HEAD /test.txt HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
        resp, status = self.send(req)
        self.close()
        if status == "200" and resp and "<html>" not in resp.lower():
            print("✓ PASSED")
            return True
        print(f"✗ FAILED (status {status}, body present? {bool(resp and '<html>' in resp.lower())})")
        return False

    def test_404(self):
        print("\n" + "="*60)
        print("TEST 4: 404 Not Found")
        if not self.connect():
            print("✗ FAILED - cannot connect")
            return False
        req = "GET /missing.html HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
        _, status = self.send(req)
        self.close()
        ok = status == "404"
        print("✓ PASSED" if ok else f"✗ FAILED (got {status})")
        return ok

    def test_403(self):
        print("\n" + "="*60)
        print("TEST 5: 403 Forbidden (directory traversal)")
        if not self.connect():
            print("✗ FAILED - cannot connect")
            return False
        req = "GET /../etc/passwd HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
        _, status = self.send(req)
        self.close()
        ok = status == "403"
        print("✓ PASSED" if ok else f"✗ FAILED (got {status})")
        return ok

    def test_304(self):
        print("\n" + "="*60)
        print("TEST 6: 304 Not Modified")
        # Get Last-Modified
        if not self.connect():
            print("✗ FAILED - cannot connect")
            return False
        req = "HEAD /future.txt HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
        resp, status = self.send(req)
        self.close()
        if not resp or status != "200":
            print("✗ FAILED - cannot retrieve future.txt (maybe missing?)")
            return False
        lm = None
        for line in resp.split('\n'):
            if 'Last-Modified:' in line:
                lm = line.split(':',1)[1].strip()
                break
        if not lm:
            print("✗ FAILED - no Last-Modified header")
            return False
        # Conditional GET with future date
        if not self.connect():
            print("✗ FAILED - cannot reconnect")
            return False
        req2 = f"GET /future.txt HTTP/1.1\r\nHost: localhost\r\nIf-Modified-Since: Thu, 31 Dec 2030 23:59:59 GMT\r\nConnection: close\r\n\r\n"
        _, status2 = self.send(req2)
        self.close()
        ok = status2 == "304"
        print("✓ PASSED" if ok else f"✗ FAILED (got {status2})")
        return ok

    def test_last_modified(self):
        print("\n" + "="*60)
        print("TEST 7: Last-Modified Header")
        if not self.connect():
            print("✗ FAILED - cannot connect")
            return False
        req = "HEAD /test.txt HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
        resp, _ = self.send(req)
        self.close()
        ok = resp is not None and 'Last-Modified:' in resp
        print("✓ PASSED" if ok else "✗ FAILED")
        return ok

    def test_400(self):
        print("\n" + "="*60)
        print("TEST 8: 400 Bad Request")
        if not self.connect():
            print("✗ FAILED - cannot connect")
            return False
        req = "GET /test.txt\r\nHost: localhost\r\n\r\n"  # missing HTTP version
        _, status = self.send(req)
        self.close()
        ok = status == "400"
        print("✓ PASSED" if ok else f"✗ FAILED (got {status})")
        return ok

    def test_persistent(self):
        print("\n" + "="*60)
        print("TEST 9: Persistent Connection (Keep-Alive)")
        if not self.connect():
            print("✗ FAILED - cannot connect")
            return False
        req1 = "GET /test.txt HTTP/1.1\r\nHost: localhost\r\nConnection: keep-alive\r\n\r\n"
        _, status1 = self.send(req1)
        req2 = "GET /index.html HTTP/1.1\r\nHost: localhost\r\nConnection: keep-alive\r\n\r\n"
        _, status2 = self.send(req2)
        self.close()
        ok = status1 == "200" and status2 == "200"
        print("✓ PASSED" if ok else f"✗ FAILED (status1={status1}, status2={status2})")
        return ok

    def test_non_persistent(self):
        print("\n" + "="*60)
        print("TEST 10: Non-Persistent Connection (Close)")
        if not self.connect():
            print("✗ FAILED - cannot connect")
            return False
        req = "GET /test.txt HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
        _, status = self.send(req)
        if status != "200":
            self.close()
            print("✗ FAILED - first request failed")
            return False
        # Try second request on same socket (should fail because connection closed)
        try:
            self.sock.settimeout(2)
            self.sock.send(b"GET /index.html HTTP/1.1\r\nHost: localhost\r\n\r\n")
            self.sock.recv(1024)
            # If we get here, connection was not closed
            self.close()
            print("✗ FAILED - connection still alive after 'close'")
            return False
        except (socket.timeout, ConnectionError, OSError):
            print("✓ PASSED")
            self.close()
            return True
        except Exception:
            self.close()
            return True

    def run_all(self):
        print("\n" + "="*70)
        print("RUNNING ALL TESTS")
        print("="*70)
        tests = [
            ("GET Text File", self.test_get_text),
            ("GET Image File", self.test_get_image),
            ("HEAD Request", self.test_head),
            ("404 Not Found", self.test_404),
            ("403 Forbidden", self.test_403),
            ("304 Not Modified", self.test_304),
            ("Last-Modified Header", self.test_last_modified),
            ("400 Bad Request", self.test_400),
            ("Persistent Connection", self.test_persistent),
            ("Non-Persistent Connection", self.test_non_persistent),
        ]
        passed = 0
        for name, func in tests:
            if func():
                passed += 1
        print("\n" + "="*70)
        print(f"RESULT: {passed}/{len(tests)} tests passed")
        print("="*70)

def main():
    print("="*70)
    print("COMP2322 Web Server Tester")
    print("Make sure the server is running on port 8080")
    print("="*70)
    tester = WebServerTester()
    tester.run_all()

if __name__ == "__main__":
    main()