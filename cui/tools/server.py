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
        return self.key()

    def key(self):
        return '%s:%s' % self.address

    @staticmethod
    def key_from_socket(socket):
        return '%s:%s' % socket.getsockname()


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
        cui.message('Listening on %s:%s' % (host, port))

        cui.update_func(self._process_sockets)
        cui.add_exit_handler(self.shutdown)

    def _accept_client(self):
        client_socket, client_address = self.server.accept()
        session = self.session_factory(client_socket)
        key = session.key()
        cui.message('Connection received from %s' % key)
        self.clients[key] = session

    def _process_sockets(self):
        sock_list = []
        if self.server:
            sock_list.append(self.server)
        sock_list.extend(map(lambda session: session.socket,
                             self.clients.values()))

        sock_read, _, _ = select.select(sock_list, [], [], 0)

        for s in sock_read:
            if s is self.server:
                self._accept_client()
            else:
                session = self.clients[self.session_factory.key_from_socket(s)]
                try:
                    session.handle()
                except (socket.error, ConnectionTerminated) as e:
                    cui.message('Connection from %s terminated' % session)
                    try:
                        session.close()
                    finally:
                        del self.clients[session.key()]

    def shutdown(self):
        self.server.close()
        for session in self.clients.values():
            try:
                session.close()
            finally:
                del self.clients[session.key()]
