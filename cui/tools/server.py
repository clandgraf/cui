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
import select
import socket

import cui


class ConnectionTerminated(Exception):
    pass


class Session(object):
    def __init__(self, socket):
        self.socket = socket
        self.address = socket.getsockname()

    def handle(self):
        pass

    def close(self):
        self.socket.close()

    def __str__(self):
        return '%s:%s' % self.address


class SocketSelector(object):
    def __init__(self):
        self._sockets = []
        self._servers = {}

    def register_socket(self, sock, server):
        if not cui.is_update_func(self._process_sockets):
            cui.message('Starting socket selector')
            cui.update_func(self._process_sockets)
        self._sockets.append(sock)
        self._servers[id(sock)] = server

    def unregister_socket(self, sock):
        self._sockets.remove(sock)
        del self._servers[id(sock)]
        if not self._sockets and cui.is_update_func(self._process_sockets):
            cui.message('Stopping socket selector')
            cui.remove_update_func(self._process_sockets)

    def _process_sockets(self):
        if not self._sockets:
            return

        sock_read, _, _ = select.select(self._sockets, [], [], 0)

        for sock in sock_read:
            self._servers[id(sock)].process_socket(sock)

socket_selector = SocketSelector()


class Server(object):
    def __init__(self, session_factory, host_var, port_var):
        super(Server, self).__init__()
        self.session_factory = session_factory
        self.host_var = host_var
        self.port_var = port_var

        self.server = None
        self.clients = collections.OrderedDict()

    def start(self):
        host = cui.get_variable(self.host_var)
        port = cui.get_variable(self.port_var)

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(5)
        cui.message('Listening on %s:%s' % self.server.getsockname())

        socket_selector.register_socket(self.server, self)
        cui.add_exit_handler(self.shutdown)

    def _accept_client(self):
        client_socket, client_address = self.server.accept()
        session = self.session_factory(client_socket)
        cui.message('Connection received from %s:%s' % session.address)
        self.clients[id(client_socket)] = session
        socket_selector.register_socket(client_socket, self)

    def process_socket(self, sock):
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
                    cui.message('Connection from %s:%s terminated' % session.address)
                    session.close()
                finally:
                    del self.clients[socket_key]
        finally:
            socket_selector.unregister_socket(sock)

    def shutdown(self):
        for session in self.clients.values():
            self.close_socket(session.socket)
        self.close_socket(self.server)
