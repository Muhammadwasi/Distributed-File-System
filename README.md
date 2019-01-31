# Distributed-File-System
## Up and Running Client and Server:
### Server Configuration:
* Run create_config.py file on each server to make a configuration file. You can edit the configuration file on your own. The command for running the create_config.py is:
  ```
  $python3 create_config.py
  ```
### Running Server: 
* If you are starting a first server, give the f optional argument as 1
```
  $python3 server.py –f 1
```
* If you are starting 3rd server or higher. Specify how many servers are already there in the distributed system by giving the optional argument s as number of already running servers.
```
  >python3 server.py –s 2 #the command is for starting 3rd server in the system.
```
### Client Running:
* Run client by this command
```
  $python3 client.py
```
## Help:
### Client Side Commands:
*	Creating a file
```
$touch [filename]
```
* Download and Open a file
```
$download [filename]
```
*	Delete a file
```
$delete [filename]
```
*	List all files
```
$dir
```
*	Close a client
```
$shutdown
```
