#!/usr/bin/env python3
import os
import platform
import sys
import socket
import selectors
import types
import psutil
import re
import uuid

sel=selectors.DefaultSelector()
messages=[b"Message 1 from client.", b"Message 2 from client", b"message 3."]
mySysOS="NIL"
global myMessage
myMessage = [b"-", b"-",b"-"]

def getProcess():
    output= "PROCESSID, PROCESSNAME, STATUS, STARTTIME\n"
    for proc in psutil.process_iter():
        try:
            #Get process name & pid from process object.
                #print(proc)
                #print(str(proc.pid), ",", srt(proc.name()), str(proc.status()), str(proc.create_time()))
            output+= str(proc.pid)+ ","+ str(proc.name()) + str(proc.status())+ ","+str(proc.create_time())+"\n"
        except(psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return output

def getConnection():
    # Retrieve network connection information based on the operating system
    connections = []
    for connection in psutil.net_connections():
        connections.append(f"Local Address: {connection.laddr}, Remote Address: {connection.raddr}, Status: {connection.status}")
    return "\n".join(connections)
    #output = "PROCESSID, STATUS, LOCALIP,LOCALPORT,REMOTEIP,REMOTEPORT\n"
    #for cons in psutil.net_connections(kind='inet'):
    #   try:
            #output+= str(cons.pid) + ","+ str(cons.status)+","+str(cons.laddr.ip)+","+str(cons.laddr.port)+","+ str(cons.raddr.ip)+","+str(cons.raddr.port)+"\n"
    #        output+= str(cons.pid) + ","+ str(cons.status)+","+str(cons.laddr.ip)+","+str(cons.laddr.port)+","+ (((str(cons.raddr).replace("()",",,")).replace))
     #   except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
      #      pass
    #return output

def getSystem():
    output= "NAME, DETAILS\n"
    output+="platform,"+ str(platform.system())+ "\n"
    output+="platform-release,"+ platform.release()+ "\n"
    output+="platform-version"+ platform.version()+ "\n"
    output+="architecture,"+ platform.machine()+ "\n"
    output+="hostname,"+ socket.gethostname()+ "\n"
    output+="ip-address," + socket.gethostbyname(socket.gethostname())+ "\n"
    output+= "mac-address"+':'.join(re.findall('..','%012x' % uuid.getnode())) + "\n"
    output+= "processor," + (platform.processor()).replace(","," ")+ "\n"
    output+= "ram,"+ str(round(psutil.virtual_memory().total / (1024.0**3))) + "  GB"
    return output

def getWinSystem():
    output=os.popen('wmic computersystem list full /format:Textvaluelist').read()
    return output

def getWinProcess():
    output=os.popen('wmic process get description, processid /fromat:csv').read()
    return output

def getWinConnection():
    output=os.popen('netstat -an').read()
    return output

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

def start_connections(host, port, num_conns, sysData):
    server_addr = (host, port)
    for i in range(0, num_conns):
        connid = i+1
        print("starting connection", connid, "to", server_addr)
        sock= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        result=sock.connect_ex(server_addr)
        print(f"connect_ex result for connection {connid}: {result}")
        #print("starting connection", connid, "to", server_addr)
        #result = sock.connect_ex(server_addr)
        print("connect_ex result:", result)

        events= selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(
            connid=connid,
            msg_total=sum(len(m) for m in sysData),
            recv_total=0,
            messages=list(sysData),
            outb=b"",
        )
        sel.register(sock, events, data=data)

def service_connection(key, mask):
    sock= key.fileobj
    data= key.data
    if mask & selectors.EVENT_READ:
        recv_data= sock.recv(10240)
        if recv_data:
            print("SERVER Recieved [", sys.getsizeof(repr(recv_data)),"] Bytes For Connection ", data.connid)
            data.recv_total += len(recv_data)
        if not recv_data or data.recv_total == data.msg_total:
            print("closing connection", data.connid)
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if not data.outb and data.messages:
            data.outb = data.messages.pop(0)
        
        if data.outb:
            # Check if the socket is connected
            error_code = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if error_code == 0:
                print(f"sending {sys.getsizeof(repr(data.outb))} bytes to connection {data.connid}")
                sent = sock.send(data.outb)
                data.outb = data.outb[sent:]
            else:
                print(f"Error in connection {data.connid}: {error_code}")

            
if len(sys.argv) !=3:
    print("usage: ", sys.argv[0], "<host> <port> ")
    sys.exit(1)

host, port= sys.argv[1:3]
host = socket.gethostbyname(host)
hostname= socket.gethostname()
myMessages=[("SYSINFO ,"+hostname+ ","+ str(host)+","+str(port)+"~`~`~`~`~\n").encode(), (getSystem()).encode()]
start_connections(host,int(port),1,myMessages)
myMessages=[("PROINFO ,"+hostname+ ","+ str(host)+","+str(port)+"~`~`~`~`~\n").encode(), (getProcess()).encode()]
start_connections(host,int(port),1,myMessages)
myMessages=[("NETINFO ,"+hostname+ ","+ str(host)+","+str(port)+"~`~`~`~`~\n").encode(), (getConnection()).encode()]
start_connections(host,int(port),1,myMessages)

print(cpu_info())

try:
    while True:
        events = sel.select(timeout=1)
        if events:
            for key, mask in events:
                service_connection(key,mask)
        if not sel.get_map():
            break
except KeyboardInterrupt:
    print("caught keybaord interrupt, exiting")
finally:
    sel.close()
    