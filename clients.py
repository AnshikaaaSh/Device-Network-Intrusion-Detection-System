#!/usr/bin/env python3
import os
import errno
import platform
import sys
import socket
import selectors
import select
import types
import psutil
import re
import uuid

sel = selectors.DefaultSelector()

def get_process():
    output = "PROCESSID, PROCESSNAME, STATUS, STARTTIME\n"
    for proc in psutil.process_iter(['pid', 'name', 'status', 'create_time']):
        try:
            output += f"{proc.info['pid']},{proc.info['name']},{proc.info['status']},{proc.info['create_time']}\n"
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return output

def get_connection():
    connections = [f"Local Address: {conn.laddr}, Remote Address: {conn.raddr}, Status: {conn.status}"
                   for conn in psutil.net_connections()]
    return "\n".join(connections)

def get_system():
    output = "NAME, DETAILS\n"
    output += f"platform,{platform.system()}\n"
    output += f"platform-release,{platform.release()}\n"
    output += f"platform-version,{platform.version()}\n"
    output += f"architecture,{platform.machine()}\n"
    output += f"hostname,{socket.gethostname()}\n"
    output += f"ip-address,{socket.gethostbyname(socket.gethostname())}\n"
    output += f"mac-address:{':'.join(re.findall('..','%012x' % uuid.getnode()))}\n"
    output += f"processor,{platform.processor().replace(',', ' ')}\n"
    output += f"ram,{round(psutil.virtual_memory().total / (1024.0**3))} GB"
    return output

def get_win_system():
    return os.popen('wmic computersystem list full /format:Textvaluelist').read()

def get_win_process():
    return os.popen('wmic process get description, processid /format:csv').read()

def get_win_connection():
    return os.popen('netstat -an').read()

def os_info():
    return platform.system()

def cpu_info():
    if platform.system() == 'Windows':
        return platform.processor()
    elif platform.system() == 'Darwin':
        command = '/usr/sbin/sysctl -n machdep.cpu.brand_string'
        return os.popen(command).read().strip()
    elif platform.system() == 'Linux':
        command = 'cat /proc/cpuinfo'
        return os.popen(command).read().strip()
    return 'platform not identified'

def start_connections(host, port, num_conns, sys_data):
    server_addr = (host, port)
    for i in range(num_conns):
        connid = i + 1
        print(f"starting connection {connid} to {server_addr}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.connect_ex(server_addr)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(
            connid=connid,
            msg_total=sum(len(m) for m in sys_data),
            recv_total=0,
            messages=list(sys_data),
            outb=b"",
        )
        sel.register(sock, events, data=data)

def is_socket_connected(sock):
    try:
        # This will raise an OSError if the socket is not connected
        sock.getpeername()
        return True
    except OSError:
        return False

def is_socket_writable(sock):
    try:
        # Attempt to send a zero-byte message to check if the socket is writable
        sock.send(b'')
        return True
    except (OSError, BrokenPipeError) as e:
        if isinstance(e, OSError) and e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
            return False
        return True

def service_connection(key, mask):
    sock = key.fileobj
    data = key.data
    try:
        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(10240)
            if recv_data:
                print(f"SERVER Received [{sys.getsizeof(repr(recv_data))}] Bytes For Connection {data.connid}")
                data.recv_total += len(recv_data)
            if not recv_data or data.recv_total == data.msg_total:
                print(f"closing connection {data.connid}")
                sel.unregister(sock)
                sock.close()
        if mask & selectors.EVENT_WRITE:
            if is_socket_writable(sock):
                if not data.outb and data.messages:
                    data.outb = data.messages.pop(0)
                if data.outb:
                    print(f"sending {sys.getsizeof(repr(data.outb))} bytes to connection {data.connid}")
                    try:
                        sent = sock.send(data.outb)
                        data.outb = data.outb[sent:]
                    except (OSError, BrokenPipeError):
                        print(f"Error in service_connection: Failed to send data to connection {data.connid}")
                        sel.unregister(sock)
                        sock.close()
            else:
                print(f"Socket not writable. Closing connection {data.connid}")
                sel.unregister(sock)
                sock.close()
    except OSError as e:
        print(f"Error in service_connection: {e}")
        sel.unregister(sock)
        sock.close()


if len(sys.argv) != 3:
    print(f"usage: {sys.argv[0]} <host> <port>")
    sys.exit(1)

host, port = sys.argv[1:3]
host = socket.gethostbyname(host)
hostname = socket.gethostname()
my_messages = [
    (f"SYSINFO,{hostname},{host},{port}~`~`~`~`~\n").encode(),
    (get_system()).encode()
]
start_connections(host, int(port), 1, my_messages)
my_messages = [
    (f"PROINFO,{hostname},{host},{port}~`~`~`~`~\n").encode(),
    (get_process()).encode()
]
start_connections(host, int(port), 1, my_messages)
my_messages = [
    (f"NETINFO,{hostname},{host},{port}~`~`~`~`~\n").encode(),
    (get_connection()).encode()
]

start_connections(host, int(port), 1, my_messages)

print(cpu_info())

try:
    while True:
        events = sel.select(timeout=1)
        if events:
            for key, mask in events:
                service_connection(key, mask)
        if not sel.get_map():
            break
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")
finally:
    sel.close()
