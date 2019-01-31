import configparser,os,socket
config =configparser.ConfigParser()
hostname=socket.gethostname()
config['DEFAULT']={'RootPath':'/home/muhammadwasi/Server/',
                   'ServerId': hostname,
                   'ClientPort':'50055',
                   'ServerPort':'50000',
                   'UdpPort':'50001',
                   'BroadcastIp':'255.255.255.255',
                   'DirectoryFileName':'directory',
                   'BroadcastPort':'50002'
                   }

with open("/home/muhammadwasi/Server/config.ini",'w') as configfile:
    config.write(configfile)

