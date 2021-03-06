# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
This module provides classes for starting servers in cui

It handles opening server sockets, accepting incoming connections
and selecting sockets with readable data ready for dispatching.

In order to open up a server you need to instantiate the server
class, which receives a factory method for Session objects.
These objects which are subclasses of Session are responsible
for handling communication over the established connection.

A simple example:

.. code-block:: python

   import cui
   import cui.server

   cui.defvariable(['mysrv', 'host'], 'localhost')
   cui.defvariable(['mysrv', 'port'], 1234)

   class Session(cui.server.Session):
       def handle(self):
           bytes_read = self.socket.recv(4096)
           # handle bytes ...

   @cui.init_func
   def start_server():
       srv = cui.server.Server(Session,
                               ['mysrv', 'host'],
                               ['mysrv', 'port'])
       srv.start()

"""

import collections
import errno
import select
import socket

import cui

from cui import tools


class ConnectionTerminated(Exception):
    pass


class Session(object):
    BUFFER_SIZE = 4096

    def __init__(self, socket, **kwargs):
        self.socket = socket
        self.address = socket.getpeername()

    def _get_input(self):
        try:
            r = self.socket.recv(Session.BUFFER_SIZE)

            if len(r) == 0:
                if len(self._read_buffer) > 0:
                    cui.message('received incomplete message: %s' % self._read_buffer)
                raise ConnectionTerminated('received 0 bytes')

            return r

        except socket.error as e:
            if e.args[0] not in [errno.EAGAIN, errno.EWOULDBLOCK]:
                raise e

        return b''

    def handle(self):
        self.handle_input(self._get_input())

    def handle_input(self, buf):
        pass

    def send_all(self, msg):
        totalsent = 0
        while totalsent < len(msg):
            sent = self.socket.send(msg[totalsent:])
            if sent == 0:
                raise ConnectionTerminated('sent 0 bytes')
            totalsent += sent

    def close(self):
        self.socket.close()

    def __str__(self):
        return '%s:%s' % self.address


class LineBufferedSession(tools.LineReader, Session):
    def handle_line(self, line):
        pass


class Server(object):
    def __init__(self, session_factory, host_var, port_var):
        super(Server, self).__init__()
        self.session_factory = session_factory
        self.host_var = host_var
        self.port_var = port_var

        self.server = None
        self.clients = collections.OrderedDict()
        self.clients_by_name = {}

    def start(self):
        host = cui.get_variable(self.host_var)
        port = cui.get_variable(self.port_var)

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(5)
        cui.message('Listening on %s:%s' % self.server.getsockname())

        cui.register_waitable(self.server, self.read)
        cui.add_exit_handler(self.shutdown)

    def _accept_client(self):
        client_socket, client_address = self.server.accept()
        session = self.session_factory(client_socket)
        cui.message('Connection received from %s:%s' % session.address)
        self.clients[id(client_socket)] = session
        self.clients_by_name[str(session)] = session
        cui.register_waitable(client_socket, self.read)

    def read(self, sock):
        if sock is self.server:
            self._accept_client()
        else:
            try:
                session = self.clients[id(sock)]
                session.handle()
            except (socket.error, ConnectionTerminated) as e:
                self.close_socket(sock)

    def close_socket(self, sock):
        socket_key = id(sock)
        try:
            if sock == self.server:
                cui.message('Closing server on %s:%s' % self.server.getsockname())
                self.server.close()
                self.server = None
            else:
                try:
                    session = self.clients.get(socket_key)
                    session_name = str(session)
                    cui.message('Connection from %s:%s terminated' % session.address)
                    session.close()
                finally:
                    del self.clients_by_name[session_name]
                    del self.clients[socket_key]
        finally:
            cui.unregister_waitable(sock)

    def shutdown(self):
        for session in self.clients.values():
            self.close_socket(session.socket)
        self.close_socket(self.server)
