import socket,argparse,os,sys
SERVER_PORT=50055
SERVER_IP=''
SEPARATOR="*"
READ_LENGTH=50
server_ip=['192.168.0.109','192.168.0.112','192.168.0.110','192.168.0.109','192.168.0.106','192.168.0.116']
sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#sock.settimeout(5)
def compose_message(message):
    return (str(len(message))+SEPARATOR+message).encode("utf-8")

    
def get_message_length(message):
    splitted_str=message.split(SEPARATOR)
    length=int(splitted_str[0])
    start_pos_to_read=len(splitted_str[0])+1
    #zero/negative when no remaining bytes are there to read
    remaining_bytes_to_read=length-(len(message)-len(splitted_str[0])-len(SEPARATOR))
    #zero/negative when no excessive bytes have been read
    excessive_bytes=len(message)-len(splitted_str[0])-len(SEPARATOR)-length
    return [length,start_pos_to_read,remaining_bytes_to_read,excessive_bytes]

def read_message(sock,remaining_data):
    
    data=''
    msg, addr = sock.recvfrom(READ_LENGTH)
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

def main():
    global sock
    isConnect=False
    parser=argparse.ArgumentParser(prog='PROG')
    parser.add_argument("-s","--serverip",help="specify the server ip to which you want to connected")
    args=parser.parse_args()
    
    if args.serverip:
        print('checking for given ip')
        SERVER_IP=args.serverip
        try:
            sock.connect((SERVER_IP,SERVER_PORT))
            
            print('connection established with '+SERVER_IP)
        except socket.error as exc:
            print("Caught an exception: "+ exc)
    else:
        print('checking for set ip')
        for ip in server_ip:
            print('checking for this: '+ip)
            SERVER_IP=ip
            try:
                sock.connect((SERVER_IP,SERVER_PORT))
                print('connection established with '+SERVER_IP)
                isConnect=True
                break
            except socket.error as exc:
                continue
        if(isConnect==False):
            print('Sorry! You can\'t access any file temporarily')
            exit(0)
    remaining_data=''
    command=input('>>')

    while(1):
        command_tok=command.split(' ')

        if(command_tok[0]=='shutdown'):
            exit(0)
        sock.send(compose_message(command))
        [data,addr,remaining_data]=read_message(sock,remaining_data)
        
        if(command_tok[0]=='download'):
            tag=data[0:3]
            if(tag=='IP:'):
                sock.close()
                SERVER_IP=data[3:len(data)]
                sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((SERVER_IP,SERVER_PORT))
                print('connection established with '+ip)
                continue
            elif(tag=='FL:'):
                with open(command_tok[1],'w') as f:
                    f.write(data[3:len(data)])
                    f.close()
                    print('File downloaded.')
                
                os.system('gedit '+command_tok[1])
                with open(command_tok[1],'r') as f:
                    size=os.path.getsize(command_tok[1])
                    try:
                        sock.send(compose_message('updatePhysical@'+command_tok[1]+'@'+f.read(size)))
                        print('File uploaded')

                    except socket.error as exc:
                        print('Can\'t upload file')
                
            else:
                print(data[3:len(data)])

        elif(data[0:3]=='NS:'):
            print('Service is not available. You can\'t access any file temporarily')
            exit(0)
        elif(data[0:3]=='IP:'):
            SERVER_IP=data[3:len(data)]
            sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((SERVER_IP,SERVER_PORT))
            print('connection established with '+SERVER_IP)
            continue
        else:
            print(data)
        command=input('>>')

main()
    
    
