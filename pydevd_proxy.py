import select
import socket

DBG_PORT = 4040
UIF_PORT = 4045

def redirect_data(from_socket, to_socket):
    r = from_socket.recv(4096)

    print(r.decode('utf-8'))

    if len(r) == 0:
        raise RuntimeError('connection broken')
    totalsent = 0
    while totalsent < len(r):
        sent = to_socket.send(r[totalsent:])
        if sent == 0:
            raise RuntimeError('connection broken')
        totalsent += sent


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('localhost', DBG_PORT))
    server.listen(5)

    print("Waiting for debugger")

    dbg_socket, dbg_addr = server.accept()

    print("Debugger connected")

    uif_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    uif_socket.connect(('localhost', UIF_PORT))

    print("User Interface connected")

    while True:
        sock_list = [dbg_socket, uif_socket]
        sock_read, _, _ = select.select(sock_list, [], [], 100)

        for s in sock_read:
            if s == dbg_socket:
                print("============== DBG ================")
                redirect_data(dbg_socket, uif_socket)
            elif s == uif_socket:
                print("============== UIF ================")
                redirect_data(uif_socket, dbg_socket)


if __name__ == '__main__':
    main()
