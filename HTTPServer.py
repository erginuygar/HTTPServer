import socket as s
import threading as t
from os import time

class HTTPServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = s.socket(s.AF_INET, s.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"HTTP Server running on {self.host}:{self.port}")

    def handle_client(self, client_socket):
        request = client_socket.recv(1024).decode()
        print(f"Received request:\n{request}")
        
        # Simple HTTP response
        response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"
        response += "<html><body><h1>Hello, World!</h1></body></html>"
        
        client_socket.sendall(response.encode())
        client_socket.close()

    def start(self):
        while True:
            client_socket, addr = self.server_socket.accept()
            print(f"Accepted connection from {addr}")
            client_thread = t.Thread(target=self.handle_client, args=(client_socket,))
            client_thread.start()