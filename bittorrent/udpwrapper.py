import logging

from tornado.ioloop import IOLoop
from datetime import timedelta

class UDPWrapper(object):
    def __init__(self, socket, io_loop=None):
        self.socket = socket
        self.socket.setblocking(False)

        self.ioloop = io_loop or IOLoop.instance()

        self._state = None
        self._read_callback = None

    def _add_io_state(self, state):
        if self._state is None:
            self._state = IOLoop.ERROR | state
            self.ioloop.add_handler(self.socket.fileno(), self._handle_events, self._state)
        elif not self._state & state:
            self._state = self._state | state
            self.ioloop.update_handler(self.socket.fileno(), self._state)

    def send_datagram(self, data):
        return self.socket.send(data)

    def receive_datagram(self, callback=None, timeout=4):
        self._read_callback = callback
        self._read_timeout = self.ioloop.add_timeout(timedelta(seconds=timeout), self.check_read_callback)
        self._add_io_state(self.ioloop.READ)
    
    def close(self):
        self.ioloop.remove_handler(self.socket.fileno())
        self.socket.close()
        self.socket = None

    def check_read_callback(self):
        if self._read_callback:
            self._read_callback(None, error='timeout')

    def _handle_read(self):
        if self._read_timeout:
            self.ioloop.remove_timeout(self._read_timeout)
        if self._read_callback:
            try:
                data = self.socket.recv(4096)
            except:
                data = None

            self._read_callback(data)
            self._read_callback = None

    def _handle_events(self, fd, events):
        if events & self.ioloop.READ:
            self._handle_read()

        if events & self.ioloop.ERROR:
            logging.error('%s event error' % self)