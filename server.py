from threading import Thread
import argparse,socket,os,signal,sys,pickle,configparser,platform,time

config=configparser.ConfigParser()

if(platform.system()=='Windows'):
    config.read('C:/Server/config.ini')
else:
    config.read('/home/muhammadwasi/Server/config.ini')

#constants
CLIENT_PORT=int(config['DEFAULT']['ClientPort'])
CLIENT_IP=""
SERVER_PORT=int(config['DEFAULT']['ServerPort'])
SERVER_IP=""
ROOT_PATH=config['DEFAULT']['RootPath']
DIRECTORY_FILE=config['DEFAULT']['DirectoryFileName']
UDP_PORT=int(config['DEFAULT']['UdpPort'])
UDP_IP=""
BROADCAST_IP=config['DEFAULT']['BroadcastIp']
BROADCAST_PORT=int(config['DEFAULT']['BroadcastPort'])
FILE_VERSION_SEPARATOR='_'
SEPARATOR="*"
READ_LENGTH=50
FORMATS="{:0>5d}"


#lists
dir_struct_list=[]
server_sockets=[]
client_sockets=[]
server_threads=[]
client_threads=[]

#variables
no_of_servers=1
global isFirst
t1=None
t2=None
current_dir=None
dir_struct=None
server_hostname=socket.gethostname()

#dictionaries
addr_to_hostname={}
hostname_to_sock={}
addr_to_server_sock={}
hostname_to_addr={}
sock_to_hostname={}



class File:
    def __init__(self, name,path,server,version=0):
        self.path = path
        self.name=name
        self.server=server
        self.version=version

class Directory:
    def __init__(self, name,path,prevdir,server):
        self.path = path
        self.elements = list()
        self.prevdir=prevdir
        self.name=name
        self.server=server
class Directory_Structure:
    def __init__(self,root):
        self.elements=list()
        self.root=root
        self.version=0
    def create_file(self,name,current_dir,server):
        path=current_dir.path+'/'+name
        file=File(name,path,server)
        current_dir.elements.append(file)
        update_dir_file()
    def create_dir(self,name,current_dir,server):
        path=current_dir.path+'/'+name+'/'
        directory=Directory(name,path,current_dir,server)
        current_dir.elements.append(directory)
        update_dir_file()
    def get_files(self,current_dir):
        files_dir=list()
        for element in current_dir.elements:
            if(type(element)==File):
                files_dir.append(element.name+':'+str(element.server))
            if(type(element)==Directory):
                files_dir.append(element.name+'/:'+str(element.server))
        return files_dir
def update_dir_file():
    with open(ROOT_PATH+DIRECTORY_FILE,'wb') as f:
        pickle.dump(dir_struct,f)
    dir_struct.version=dir_struct.version+1
    

udp_sock= socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
udp_sock.bind((UDP_IP, UDP_PORT))

broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
broadcast_sock.bind((SERVER_IP, BROADCAST_PORT))

tcp_server_sock= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_server_sock.bind((SERVER_IP, SERVER_PORT))

tcp_client_sock= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_client_sock.bind((CLIENT_IP, CLIENT_PORT))



if(os.path.isfile(ROOT_PATH+DIRECTORY_FILE) and os.path.getsize(ROOT_PATH+DIRECTORY_FILE)>0):
    fd=open(ROOT_PATH+DIRECTORY_FILE,'rb')
    dir_struct=pickle.load(fd)
    current_dir=dir_struct.root
    print('Loading directory structure from file...')
    fd.close()
else:
    root_dir=Directory('root','/',None,server_hostname)
    current_dir=root_dir
    dir_struct=Directory_Structure(root_dir)
    update_dir_file()
    print('Creating new directory structure...')


def get_message_length(message):
    splitted_str=message.split(SEPARATOR)
    length=int(splitted_str[0])
    start_pos_to_read=len(splitted_str[0])+1
    #zero/negative when no remaining bytes are there to read
    remaining_bytes_to_read=length-(len(message)-len(splitted_str[0])-len(SEPARATOR))
    #zero/negative when no excessive bytes have been read
    excessive_bytes=len(message)-len(splitted_str[0])-len(SEPARATOR)-length
    return [length,start_pos_to_read,remaining_bytes_to_read,excessive_bytes]

def compose_message(message):
    if(type(message)==bytes):
        return (str(len(message))+SEPARATOR+str(message)).encode("utf-8")
    else:
        return (str(len(message))+SEPARATOR+message).encode("utf-8")

def sig_int_handler(sig,frame):
    print("Updating directory file")
    print('No of client_sockets:'+str(len(client_sockets)))
    print('No of server_sockets:'+str(len(server_sockets)))

    for s in client_sockets:
        if(len(server_sockets)==0):
            s.send(compose_message('NS: No server Avaialble'))
        else:
            ip_addr=hostname_to_addr[sock_to_hostname[server_sockets[0]]]
            print(ip_addr)
            s.send(compose_message('IP:'+ip_addr))
    print('Closing all the sockets')
    tcp_client_sock.shutdown(0)
    tcp_server_sock.shutdown(0)
    udp_sock.close()
    broadcast_sock.close()
    tcp_client_sock.close()
    tcp_server_sock.close()
    for sock in server_sockets:
        sock.shutdown(0)
        sock.close()
    for sock in client_sockets:
        sock.shutdown(0)
        sock.close()
    sys.exit(0)


def read_message(sock,remaining_data):
    
    data=''
    msg, addr = sock.recvfrom(READ_LENGTH) 
    if(len(msg)==0):
        return ['',addr,remaining_data]
    msg=msg.decode("utf-8")

    if(len(remaining_data)>0):
        msg=remaining_data+msg
        
    [length,start_pos_to_read,remaining_bytes_to_read,excessive_bytes]=get_message_length(msg)
    if(remaining_bytes_to_read>0):
        data=data+msg[start_pos_to_read:len(msg)]
        msg, addr = sock.recvfrom(remaining_bytes_to_read)
        msg=msg.decode("utf-8")
        data=data+msg
    elif(excessive_bytes>0):
        data=data+msg[start_pos_to_read:len(msg)-excessive_bytes]
        remaining_data=msg[len(msg)-excessive_bytes:len(msg)]
    else:
        data=data+msg[start_pos_to_read:len(msg)]
    return [data,addr,remaining_data]

def read_message_pickle(sock,remaining_data):
    
    data=''
    msg, addr = sock.recvfrom(5)
    if(len(msg)==0):
        return ''
    msg=msg.decode("utf-8")
    size=int(msg)
    data, addr = sock.recvfrom(size)
    return data

def accept_server_thread():
    global hostname_to_sock,hostname_to_addr,server_sockets
    global sock_to_hostname,addr_t_server_sock,addr_to_hostname
    tcp_server_sock.listen(5)
    while(1):
        print('accepting server conns')
        print(addr_to_hostname)
        sock,addr=tcp_server_sock.accept()
        
        #updating lists and dictionaries 
        addr_to_server_sock[addr[0]]=sock
        hostname=addr_to_hostname[addr[0]]
        hostname_to_sock[hostname]=sock
        hostname_to_addr[hostname]=addr[0]
        sock_to_hostname[sock]=hostname
        server_sockets.append(sock)
        
        #sending dir_struct to the server
        data=pickle.dumps(dir_struct)
        size=len(data)
        size=FORMATS.format(size)
        sock.send((size).encode("utf-8"))
        sock.send(data)
        
        #creating a thread to handle this server's requests
        t=Thread(target=handle_server_thread,args=(sock,hostname,addr[0]))
        t.daemon=True
        server_threads.append(t)
        t.start()
        print('server conn accepted')

def accept_client_thread():
    global client_sockets
    tcp_client_sock.listen(5)
    while(1):
        print('accepting client conns')
        sock,addr=tcp_client_sock.accept()
        client_sockets.append(sock)

        #creating thread to handle this client's request
        t=Thread(target=handle_client_thread,args=(sock,addr[0]))
        t.daemon=True
        client_threads.append(t)
        t.start()
        print('client conn accepted')
        

def handle_server_thread(sock,hostname,ip_addr):
    global dir_struct,current_dir
    global addr_to_hostname,addr_to_server_sock,hostname_to_sock,hostname_to_addr
    global sock_to_hostname,server_sockets
    remaining_data=''
    while(1):
        [cmd,addr,remaining_data]=read_message(sock,remaining_data)
        if(len(cmd)==0):
            del addr_to_hostname[ip_addr]
            del addr_to_server_sock[ip_addr]
            del hostname_to_sock[hostname]
            del hostname_to_addr[hostname]
            del sock_to_hostname[sock]
            server_sockets.remove(sock)
            sock.close()
            print('Server Disconnected: '+ip_addr+'@'+hostname)
            return
        if(cmd=='dir_struct'):
            data=read_message_pickle(sock,'')
            dir_struct=pickle.loads(data)
            current_dir=dir_struct.root
            update_dir_file()
            print('directory list updated')
            continue
        if(cmd[0:14]=='updatePhysical'):
            data=cmd.split('@')
            for file in current_dir.elements:
                if(file.name==data[1]):
                    file.version=file.version+1
                    print('file updated virtually:'+data[1])
                    if(server_hostname in file.server):
                        with open(ROOT_PATH+data[1],'w') as f:
                            for i in range(2,len(data)):
                                f.write(data[i])
                                f.close()
                                print('File Updated physically:'+data[1])
                                update_dir_file()
                    break
            continue
        data=cmd.split(' ')

        print('require update:'+cmd)
        if(data[0]=='virtual' and data[1]=='mkdir'):
            dir_struct.create_dir(data[2],current_dir,data[3])
        if(data[0]=='virtual' and data[1]=='touch'):
            dir_struct.create_file(data[2],current_dir,[data[3],data[4]])
        if(data[0]=='replicate' and data[1]=='touch'):
            os.system('touch '+ROOT_PATH+data[2])
            print('file created:'+data[2])
            dir_struct.create_file(data[2],current_dir,[data[3],data[4]])
        if(data[0]=='updateVirtual'):
            update_dir_ver_by_filename(data[1])
            print('file updated virtually'+data[1])
        
        
        if(data[0]=='delVirFile' and data[1]=='delete'):
            for file in current_dir.elements:
                if(file.name==data[2]):
                    current_dir.elements.remove(file)
                    update_dir_file()
                    if(server_hostname in file.server):
                        os.remove(ROOT_PATH+file.name)
                        print('File deleted: '+data[1])
                    break
        if(data[0]=='delVirDir' and data[1]=='delete'):
            for file in current_dir.elements:
                if(file.name==data[2]):
                    current_dir.elements.remove(file)
                    update_dir_file()
                    if(server_hostname in file.server):
                        #os.rmdir(ROOT_PATH+file.name)
                        print('Directory deleted: '+data[1])
                    break
        if(data[0]=='getFile'):
            with open(ROOT_PATH+data[1]) as f:
                size=os.path.getsize(ROOT_PATH+data[1])
                sock.send(compose_message(f.read(size)))
                print('File sent: '+data[1])
            
                
def list_to_str(my_list):
    string=''
    for item in my_list:
        string=string+'\n'+my_list
    return string

def update_dir_ver_by_filename(fname):
    global current_dir
    for file in current_dir.elements:
        if(file.name==fname):
            file.version=file.version+1
            
def handle_client_thread(sock,ip_addr):
    global server_hostname,current_dir,client_sockets,server_sockets,dir_struct
    remaining_data=''
    while(1):
        [cmd,addr,remaining_data]=read_message(sock,remaining_data)
        if(len(cmd)==0):
            client_sockets.remove(sock)
            sock.close()
            print('Client Disconnected: '+ip_addr)
            return
        if(cmd[0:14]=='updatePhysical'):
            data=cmd.split('@')
            print('update request came:'+data[1])
            for s in server_sockets:
                print(s)
                s.send(compose_message(cmd))
            for file in current_dir.elements:
                if(file.name==data[1]):
                    file.version=file.version+1
                    print('file updated virtually:'+data[1])
                    if(server_hostname in file.server):
                        with open(ROOT_PATH+data[1],'w') as f:
                            for i in range(2,len(data)):
                                f.write(data[i])
                                f.close()
                                print('File Updated physically:'+data[1])
                                update_dir_file()
                            break
                else:
                    print("File not found")
            continue
        data=cmd.split(' ')
        if(data[0]=='dir'):
            #directories=list_to_str(os.listdir('\home\\'))
            sock.send(compose_message(str(dir_struct.get_files(current_dir))))
            #updating dir_struct of all servers
        elif(data[0]=='mkdir'):
            dir_struct.create_dir(data[1],current_dir,server_hostname)
            update_dir_file()

            sock.send(compose_message(data[1]+' directory created'))
            for s in server_sockets:
                s.send(compose_message('virtual mkdir '+data[1]+' '+server_hostname))
        elif(data[0]=='touch'):
            
            if(len(server_sockets)>0):
                second_sock=server_sockets[0]
                second_hostname=sock_to_hostname[server_sockets[0]]
                
                dir_struct.create_file(data[1],current_dir,[server_hostname,second_hostname])
                update_dir_file()
                #os.system('type nul > '+ROOT_PATH+data[1])
                os.system('touch '+ROOT_PATH+data[1])
                second_sock.send(compose_message('replicate touch '+data[1]+' '+server_hostname+' '+second_hostname))
                sock.send(compose_message(data[1]+' file created'))
                for s in server_sockets[1:len(server_sockets)]:
                    s.send(compose_message('virtual touch '+data[1]+' '+server_hostname+' '+second_hostname))
            else:
                dir_struct.create_file(data[1],current_dir,[server_hostname])
                os.system('touch '+ROOT_PATH+data[1])
                update_dir_file()
                sock.send(compose_message(data[1]+' file created'))
                for s in server_sockets:
                    s.send(compose_message('virtual touch '+data[1]+' '+[server_hostname]))



        elif(data[0]=='delete'):
            isFileFound=False
            for file in current_dir.elements:
                if(file.name==data[1]):
                    if(type(file)==File):
                        isFileFound=True
                        current_dir.elements.remove(file)
                        update_dir_file()
                        for s in server_sockets:
                            s.send(compose_message('delVirFile delete '+data[1]))
                        if(server_hostname in file.server):
                            os.remove(ROOT_PATH+file.name)
                            sock.send(compose_message('File Deleted.'))
                            print('File deleted: '+data[1])
                    elif(type(file)==Directory):
                        isFileFound=True
                        current_dir.elements.remove(file)
                        update_dir_file()
                        for s in server_sockets:
                            s.send(compose_message('delVirDir delete '+data[1]))
                        if(server_hostname in file.server):
                            #os.rmdir(ROOT_PATH+file.name)
                            sock.send(compose_message('Directory Deleted.'+data[1]))
                            print('Directory deleted: '+data[1])
                    break
            if(isFileFound==False):
                sock.send(compose_message('ER:No such file with name '+data[1]))

        elif(data[0]=='download'):
            isFileFound=False
            isSent=False
            for file in current_dir.elements:
                if(file.name==data[1]):
                    if(type(file)==File):
                        isFileFound=True
                        if(len(file.server)==1):
                            if(file.server[0]==server_hostname):
                                with open(ROOT_PATH+file.name) as f:
                                    size=os.path.getsize(ROOT_PATH+file.name)
                                    sock.send(compose_message('FL:'+f.read(size)))
                                    print('File sent: '+file.name)
                            elif(file.server[0] in hostname_to_addr):
                                sock.send(compose_message('IP:'+hostname_to_addr[file.server[0]]))
                                print('IP address sent')
                            else:
                                sock.send(compose_message('ER:File is temporarily unavailable'))
                        elif(len(file.server)==2):
                            for fs in file.server:
                                if(fs ==server_hostname):
                                    with open(ROOT_PATH+file.name) as f:
                                        size=os.path.getsize(ROOT_PATH+file.name)
                                        sock.send(compose_message('FL:'+f.read(size)))
                                        print('File sent: '+file.name)
                                        isSent=True

                                        break
                                elif(fs in hostname_to_addr):
                                    sock.send(compose_message('IP:'+hostname_to_addr[fs]))
                                    print('IP address sent')
                                    isSent=True
                                    break
                            if(isSent==False):
                                sock.send(compose_message('ER:File is temporarily unavailable'))
                                
                    else:
                        sock.send(compose_message('ER:Can\'t open '+data[1]+' because it is a directory.'))
            if(isFileFound==False):
                sock.send(compose_message('ER:No such file with name '+data[1]))
        else:
            sock.send(compose_message('Wrong Command'))

            
def read_from_screen():
    remaining_data=''
    [cmd,addr,remaining_data]=read_message(0,remaining_data)
    data=cmd.split(' ')
    if(data[0]=='shutdown'):
        pid=os.getpid()
        os.kill(pid,signal.SIGINT)
def update_stale_files(most_updated_list,stale_list):
    updated_dir=most_updated_list.root
    stale_dir=stale_list.root
    for up_file in updated_dir.elements:
        for st_file in stale_dir.elements:
            if(up_file.name==st_file.name and server_hostname in up_file.server and up_file.version>st_file.version):
                print('Most updated file version'+str(up_file.version))
                print('Current file version'+str(st_file.version))

                if(up_file.server[0]!=server_hostname):
                    sock=hostname_to_sock[up_file.server[0]]
                else:
                    sock=hostname_to_sock[up_file.server[1]]
                if(sock in server_sockets):
                    sock.send(compose_message("getFile "+up_file.name))
                    [data, addr, remaining_data]=read_message(sock,'')
                    with open(ROOT_PATH+up_file.name,'w') as f:
                        f.write(data)
                        f.close()
                        print('Replicated file Updated physically:'+up_file.name)
    fileFound=False
    for st_file in stale_dir.elements:
        if server_hostname in st_file.server:
            for up_file in updated_dir.elements:
                if(st_file.name==up_file.name):
                    fileFound=True
                    break;
            if(fileFound==False):
                try:
                    os.remove(ROOT_PATH+st_file.name)
                    print('Replicated file removed physically:'+st_file.name)
                except Exception as exc:
                    print('File I/o not completed')
            fileFound=False

            
                    

                
        
def main():
    signal.signal(signal.SIGINT,sig_int_handler)
    global isFirst,no_of_servers,current_dir,dir_struct,dir_struct_list
    global addr_to_hostname,hostname_to_sock,hostname_to_addr,sock_to_hostname,addr_to_server_sock,server_sockets
    remaining_data_broad=''
    remaining_data_udp=''
    parser=argparse.ArgumentParser(prog='PROG')
    parser.add_argument("-f","--isfirst",help="specify if it's a first server to operate")
    parser.add_argument("-s","--servers",help="specify number of servers",type=int)

    args=parser.parse_args()

    #dir_struct_list for getting from each server
    #threads starting for accepting client and server connections
    t1=Thread(target=accept_server_thread,args=())
    t1.daemon=True
    t2=Thread(target=accept_client_thread,args=())
    t2.daemon=True
    
    global dir_struct_list

    if args.servers:
        no_of_servers=args.servers
    if args.isfirst:
        print('No broadcast.')
        isFirst=True    
    else:
        print('Broadcasting request for registering ip')
        isFirst=False
        broadcast_sock.sendto(compose_message(socket.gethostname()),(BROADCAST_IP,BROADCAST_PORT))
        print("connection request broadcasted!")
        
        #consumed the request message send to itself
        [data,addr,remaining_data_broad]=read_message(broadcast_sock,remaining_data_broad)
        
        #getting acknowlegments from every server:
        for i in range(no_of_servers):
            
            #reading ack and hostname
            [reply,addr,remaining_data_udp]=read_message(udp_sock,remaining_data_udp)
            if(len(reply)==0):
                print('Server is getting shutdown.')
            if(reply[0:3]=='ack'):
                print("ack received")
                
                
                #creating tcp socket with the server
                tcp_sock2= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tcp_sock2.connect((addr[0],SERVER_PORT))
                
                hostname=reply[3:len(reply)]
                addr_to_hostname[addr[0]]=hostname
                hostname_to_sock[hostname]=tcp_sock2
                hostname_to_addr[hostname]=addr[0]
                sock_to_hostname[tcp_sock2]=hostname
                print("a server with ip "+str(addr[0])+" port:"+str(addr[1])+" has been added")
                server_sockets.append(tcp_sock2)
                addr_to_server_sock[addr[0]]=tcp_sock2
                
                data=read_message_pickle(tcp_sock2,'')
                dir_struct_list.append(pickle.loads(data))
                
                #starting thread to accept incoming requests from server 
                t=Thread(target=handle_server_thread,args=(tcp_sock2,hostname,addr[0]))
                t.daemon=True
                server_threads.append(t)
        dir_struct_list.append(dir_struct)
        most_updated_list=dir_struct_list[0]            
        for dir_list in dir_struct_list:
            if(most_updated_list.version<dir_list.version):
                most_updated_list=dir_list
        if(dir_struct==most_updated_list):
            print('Current list is the most updated one. Sending my list to others...')
            for sock in server_sockets:
                sock.send(compose_message('dir_struct'))
                data=pickle.dumps(dir_struct)
                size=len(data)
                size=FORMATS.format(size)
                sock.send((size).encode("utf-8"))
                sock.send(data)
        #creating, deleting, and updating replicated files that have been changed after it went to shutdown
        print('Most updated list version:'+str(most_updated_list.version))
        print('Current list version:'+str(dir_struct.version))

        update_stale_files(most_updated_list,dir_struct)
        dir_struct=most_updated_list
        current_dir=dir_struct.root
        update_dir_file()
        print('list taken from all')
        #starting all server threads
        for t in server_threads:
            t.start()
    #starting accepting client and server connections
    t2.start()
    t1.start()
    while True:
        print("accepting registering ips")
        
        [hostname,addr,remaining_data_broad]=read_message(broadcast_sock,remaining_data_broad)
        if(len(hostname)==0):
            print("Server is getting shutdown.")
        addr_to_hostname[addr[0]]=hostname
        print(addr_to_hostname)    
            
        print(addr[0])

        #sending ack and hostname to the server
        print("received conn request from %s:%s : %s"%(addr[0],addr[1],hostname))
        udp_sock.sendto(compose_message(('ack'+socket.gethostname())),(addr[0],UDP_PORT))
        print("ip registered and ack sent")
    

main()
