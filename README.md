================================================================================
COMP2322 Computer Networking - Multi-threaded Web Server
================================================================================

Student Name: Uygar Ergin
Student ID: 25089266d

================================================================================
1. Requirements
================================================================================
- Python 3.6 or higher
- No external libraries (uses only standard library)

================================================================================
2. How to Run the Server
================================================================================
1. Open a terminal.
2. Navigate to the directory containing webserver.py.
3. Run: python webserver.py

The server will start on http://0.0.0.0:8080 and serve files from the 'www' folder.
If the 'www' folder does not exist, it will be created automatically along with
sample files (index.html, test.txt, future.txt). Image files must be placed manually.

================================================================================
3. How to Test the Server
================================================================================
You can use any web browser, curl, or the provided test_webserver.py script.

3.1 Using curl (command line examples):
----------------------------------------
# GET a text file
curl -v http://127.0.0.1:8080/test.txt

# GET an image file (place your own image in www/ first)
curl -v http://127.0.0.1:8080/your_image.jpg --output image.jpg

# HEAD request
curl -I http://127.0.0.1:8080/test.txt

# Test 404 Not Found
curl -v http://127.0.0.1:8080/nonexistent.html

# Test 403 Forbidden (directory traversal)
curl -v http://127.0.0.1:8080/../etc/passwd

# Test 304 Not Modified
curl -v -H "If-Modified-Since: Thu, 31 Dec 2030 23:59:59 GMT" http://127.0.0.1:8080/future.txt

# Test persistent connection (two requests on same socket)
curl -v http://127.0.0.1:8080/test.txt http://127.0.0.1:8080/index.html

# Test non-persistent connection
curl -v -H "Connection: close" http://127.0.0.1:8080/test.txt

3.2 Using the automated tester:
--------------------------------
python test_webserver.py

This will run 10 tests and report PASS/FAIL for each.

================================================================================
4. Project Structure
================================================================================
project/
├── webserver.py          # Main server program
├── test_webserver.py     # Automated test script
├── server.log            # Log file (auto-generated)
├── README.txt            # This file
└── www/                  # Document root
    ├── index.html        # Sample HTML (auto-created)
    ├── test.txt          # Sample text (auto-created)
    ├── future.txt        # For 304 testing (auto-created)
    └── (your images)     # Place image files here

================================================================================
5. Troubleshooting
================================================================================
- Port already in use: Change SERVER_PORT in webserver.py (e.g., to 8888).
- Permission denied: Make sure you have write access to the current directory.
- Connection refused: Ensure the server is running before testing.

================================================================================
6. Features Supported
================================================================================
- Multi-threading (one thread per client)
- GET and HEAD methods
- Text, HTML, and image files
- Persistent (keep-alive) and non-persistent (close) connections
- Status codes: 200, 400, 403, 404, 304
- Last-Modified and If-Modified-Since headers
- Logging to server.log
- Path traversal protection