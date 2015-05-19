import socket
from usiserver import *

CODE = "GVM_DRAW70"

def client(string):
    HOST, PORT = 'localhost', 12593
    # SOCK_STREAM == a TCP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #sock.setblocking(0)  # optional non-blocking
    sock.connect((HOST, PORT))
    print "Sending: " + string
    sock.send(string)
    reply = sock.recv(16384)  # limit reply to 16K
    sock.close()
    return reply

print client(checkconnect_msg(CODE_GVM_DRAW))