"""
Socket bridge for Electron UI communication.
Provides a TCP socket server that sends/receives JSON messages to/from Electron.
"""

import json
import socket
import threading
from typing import Callable, Optional


class SocketBridge:
    """TCP socket server for Electron UI communication."""

    def __init__(self, port: int = 9999):
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.client_socket: Optional[socket.socket] = None
        self.running = False
        self._receive_thread: Optional[threading.Thread] = None
        self._accept_thread: Optional[threading.Thread] = None

        # Message handlers
        self._handlers: dict[str, Callable] = {}

    def on(self, action: str, handler: Callable):
        """Register a handler for an action type."""
        self._handlers[action] = handler

    def start(self):
        """Start the socket server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('127.0.0.1', self.port))
        self.server_socket.listen(1)
        self.running = True

        # Start accept thread
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()

        print(f"Socket bridge listening on port {self.port}")

    def _accept_loop(self):
        """Accept incoming connections."""
        while self.running:
            try:
                self.server_socket.settimeout(1.0)
                try:
                    client, addr = self.server_socket.accept()
                    print(f"Electron UI connected from {addr}")
                    self.client_socket = client
                    self._start_receive_thread()
                except socket.timeout:
                    continue
            except Exception as e:
                if self.running:
                    print(f"Accept error: {e}")

    def _start_receive_thread(self):
        """Start receiving messages from client."""
        if self._receive_thread and self._receive_thread.is_alive():
            return
        self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._receive_thread.start()

    def _receive_loop(self):
        """Receive messages from Electron."""
        buffer = ""
        while self.running and self.client_socket:
            try:
                self.client_socket.settimeout(1.0)
                try:
                    data = self.client_socket.recv(4096)
                    if not data:
                        print("Electron UI disconnected")
                        self.client_socket = None
                        break
                    buffer += data.decode('utf-8')

                    # Process complete messages (newline-delimited JSON)
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            self._handle_message(line)
                except socket.timeout:
                    continue
            except Exception as e:
                if self.running:
                    print(f"Receive error: {e}")
                self.client_socket = None
                break

    def _handle_message(self, message: str):
        """Handle incoming message from Electron."""
        try:
            data = json.loads(message)
            action = data.get('action') or data.get('type')

            if action and action in self._handlers:
                # Call handler with the data
                handler = self._handlers[action]
                # Run handler in a thread to not block
                threading.Thread(
                    target=handler,
                    args=(data,),
                    daemon=True
                ).start()
            else:
                print(f"Unknown action: {action}")
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}")

    def send(self, message_type: str, **kwargs):
        """Send a message to Electron."""
        if not self.client_socket:
            return False

        try:
            msg = {'type': message_type, **kwargs}
            data = json.dumps(msg) + '\n'
            self.client_socket.sendall(data.encode('utf-8'))
            return True
        except Exception as e:
            print(f"Send error: {e}")
            self.client_socket = None
            return False

    def send_transcript(self, text: str):
        """Send transcript update."""
        self.send('transcript', text=text)

    def send_notes(self, text: str):
        """Send notes update."""
        self.send('notes', text=text)

    def send_suggestion(self, text: str):
        """Send suggestion."""
        self.send('suggestion', text=text)

    def send_answer(self, text: str):
        """Send answer to question."""
        self.send('answer', text=text)

    def send_topic(self, text: str):
        """Send topic update."""
        self.send('topic', text=text)

    def send_status(self, status: str):
        """Send status update (loading, ready, etc)."""
        self.send('status', status=status)

    def stop(self):
        """Stop the socket server."""
        self.running = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
