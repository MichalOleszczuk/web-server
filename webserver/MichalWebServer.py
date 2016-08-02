import errno
import os
import signal
import socket
import sys
import getopt
from io import StringIO
from mimetypes import guess_type
import config
import traceback

REQUEST_QUEUE_SIZE = 1024

def serve_forever(argv):
    server_host = config.server_host
    server_location = config.server_location
    server_port = config.server_port
    default_home = config.default_home
    default_file = config.default_file
    try:
        opts, args = getopt.getopt(argv, 'hl:p:i:f:o:', ["help", "location=", "port=", "host=", "file=", "home="])
    except getopt.GetoptError:
        print('Command line options:\n'
              '-h or --help for help\n'
              '-l or --location to set location (takes argument)\n'
              '-p or --port to set server port (takes argument)\n'
              '-i or --host to set server host (takes argument)\n'
              '-f or --file to set default page (index.html as default\n'
              '-o or --home to set home page URL. If FALSE http://localhost:8888/index.html if\n'
              'if TRUE http://localhost:8888/ (takes argument)')
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print('Command line options:\n'
                  '-h or --help for help\n'
                  '-l or --location to set location (takes argument)\n'
                  '-p or --port to set server port (takes argument)\n'
                  '-i or --host to set server host (takes argument)\n'
                  '-f or --file to set default page (index.html as default\n'
                  '-o or --home to set home page URL. If FALSE http://localhost:8888/index.html if\n'
                  'if TRUE http://localhost:8888/ (takes argument)')
            sys.exit()
        elif opt in ('-l', '--location'):
            server_location = arg
            print('Location changed to:' +arg)
        elif opt in ('-p', '--port'):
            server_port = int(arg)
            print('Port changed to:' +arg)
        elif opt in ('-i', '--host'):
            server_host = arg
            print('Host changed to:' +arg)
        elif opt in ('-f', '--file'):
            default_file = arg
            print('Default file changed to:' +arg)
        elif opt in ('-o', '--home'):
            default_home = arg
            print("Home URL equal to:" +arg)

    SERVER_ADDRESS = (HOST, PORT) = server_host, server_port
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind(SERVER_ADDRESS)
    listen_socket.listen(REQUEST_QUEUE_SIZE)
    print('Serving HTTP on port {port} ...'.format(port=PORT))

    signal.signal(signal.SIGCHLD, grim_reaper)

    while True:
        try:
            client_connection, client_address = listen_socket.accept()
        except IOError as e:
            code, msg = e.args
            # restart 'accept' if it was interrupted
            if code == errno.EINTR:
                continue
            else:
                raise

        pid = os.fork()
        if pid == 0:  # child
            listen_socket.close()  # close child copy
            handle_request(client_connection)
            client_connection.close()
            os._exit(0)
        else:  # parent
            client_connection.close()  # close parent copy and loop over


def grim_reaper(signum, frame):
    while True:
        try:
            pid, status = os.waitpid(
                -1,          # Wait for any child process
                 os.WNOHANG  # Do not block and return EWOULDBLOCK error
            )
        except OSError:
            return

        if pid == 0:  # no more zombies
            return

def handle_request(client_connection):
    try:
        request = client_connection.recv(1024)
        request_text = request.decode()
        rfile = StringIO(request_text)
        raw_requestline = rfile.readline()
        shiet = raw_requestline.split()
        met = shiet[0]
        url = shiet[1][1:]
        destination = os.path.join(config.server_location, url)

        if url == 'redirect':
            print('Redirect')
            http_response = b"""HTTP/1.1 301 Moved Permanently
Location: """ + bytes(os.path.join(config.server_host, 'dupa.txt'), 'utf-8') + b"""\n\n"""
            client_connection.sendall(http_response)
            return

        if url == '' and config.default_home:
            print('Home')
            with open(config.default_file, 'rb') as htmlDisplay:
                textDisplay = htmlDisplay.read()
                content_type, encoding = guess_type(config.default_file, True)
                http_response = b"""HTTP/1.1 200 OK\nContent-Type: """ + bytes(content_type, 'utf-8') + b"""\n\n""" + textDisplay
                client_connection.sendall(http_response)
                return
        elif url == '' and not config.default_home:
            print('Home')
            http_response = b"""HTTP/1.1 301 Moved Permanently
Location: """ + bytes(os.path.join(config.server_host, config.default_file), 'utf-8') + b"""\n\n"""
            client_connection.sendall(http_response)
            return

        try:
            with open(destination, 'rb') as fileDisplay:
                textDisplay = fileDisplay.read()
                content_type, encoding = guess_type(destination, True)
                http_response = b"""HTTP/1.1 200 OK \nContent-Type: """ + bytes(content_type, 'utf-8') + b""" \n\n""" + textDisplay

        except FileNotFoundError:
            http_response = b"""HTTP/1.1 404 Not Found \n
Error 404: Page not found
                """
        except IsADirectoryError:
            http_response = b"""HTTP/1.1 200 OK \n
""" + bytes('\n'.join(os.listdir(destination)).encode('utf-8'))

    except Exception as e:
        http_response = b"""HTTP/1.1 500 Internal Server Error \n
""" + bytes(traceback.format_exc())

    client_connection.sendall(http_response)

if __name__ == '__main__':
    serve_forever(sys.argv[1:])