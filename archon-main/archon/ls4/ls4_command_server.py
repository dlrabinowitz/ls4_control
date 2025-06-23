# define LS4_Command_Server class.

# This is a creates a basic TCP server to receive commands, execute them, and return
# a reply


import sys
import os
import select
import socket
import asyncio
#import logging
from archon.controller.ls4_logger import LS4_Logger   
from archon.ls4.ls4_status import LS4_Status
from archon.ls4.ls4_abort  import LS4_Abort 
from . import DEFAULT_COMMAND_PORT, DEFAULT_STATUS_PORT, DEFAULT_MAXBUFSIZE, DEFAULT_TIMEOUT,\
              DONE_REPLY, ERROR_REPLY, SHUTDOWN_COMMAND, RESTART_COMMAND, REBOOT_COMMAND


class LS4_Command_Server():

    """ Class to manage command server for LS4_Control_Program """

    # recognized camera commands
    default_command_dict={\
        'init':{'arg_name_list':[],'comment':'initialize camera controller'},\
        'open shutter':{'arg_name_list':[],'comment':'open the camera shutter'},\
        'close shutter':{'arg_name_list':[],'comment':'close the camera shutter'},\
        'status':{'arg_name_list':[],'comment':'return camera status'},\
        'clear':{'arg_name_list':[],'comment':'clear the camera'},\
        'r':{'arg_name_list':['num_lines','file_root'],\
             'comment':'readout num_lines from camera and write to file'},\
        'h':{'arg_name_list':['key_word','value'],\
             'comment':'add keyword/value to image fits header'},\
        'e':{'arg_name_list':['shutter','exptime','fileroot'],\
            'comment':' expose for exptime sec with shutter open (True,False) and savee file'}\
        }

    async def default_command_function(self,command=None,arg_value_list=None,reply_list=None):

        if command is not None:
           self.debug("command_function: command and args are [%s] [%s]" %\
                     (command,arg_value_list) )

        reply_list[0] = DONE_REPLY
        self.debug("command_function: reply is %s" % reply_list[0])


    def __init__(self,host=None,port=None,maxbufsize=None,timeout=None, \
                 command_fnc=None, logger=None, command_dict=None, \
                 max_connections=2, polling_timeout = 10,\
                 done_reply=DONE_REPLY,error_reply=ERROR_REPLY, server_status=None,
                 status_only = False, ls4_abort=None):

        """
        Specify host name, TCP ports for command and status, maximum buffer size,
        command timeout (sec), function to process commands, logger , 
        dictionary of commands, maxumum number of connections,
        polling timeout (msec), and expected replies from the command function when 
        successful (done_reply) or when there is an error (error_reply).
        
        logger is and instance of LS4_Logger, and must provide member functions 
        info,warn,error,debug, and critical.

        The command dictionary supplies all possible commands as keys to the dictionary, with
        each key associated with a description of the command. Each description is of the form
        {'arg_name_list':arg_list;'comment':comment_string}, where arg_list is the list of argument
        names (an empty list if there are no arguments), and comment_string  explains what
        the command is for.
       
        The command function must expect three arguments: 
          command: the command name (the keys in the command dictionary)
        
          arg_value_list: a list of the values provided for the arguments, in the order in which they
           appear in the command dictionary.
        
          reply_string: a list whose only member is a placeholder for command reply.
        
        The reply string must begin with done_reply or error_reply  followed
        by an optional string with additional explanation.

        server_status must be an instance of LS4_Status

        To disable all commands except status, set status_only = True

        ls4_abort is an instance of the LS4_Abort class to handle aborting. If
        None, then aborts are not handled by the command server.

        """        

        self.port = DEFAULT_COMMAND_PORT
        self.timeout = DEFAULT_TIMEOUT
        self.maxbufsize = DEFAULT_MAXBUFSIZE
        self.command_fnc = self.default_command_function
        self.max_connections = max_connections
        self.polling_timeout = polling_timeout

        if ls4_abort is not None:
           assert isinstance(ls4_abort,(LS4_Abort)),"ls4_abort is not an instance of LS4_Abort"

        self.ls4_abort = ls4_abort
        

        if status_only in [True,False]:
           self.status_only = status_only
        else:
           self.status_only = False

        assert isinstance(server_status,(LS4_Status)), "server_status is not instantiated"
        self.server_status = server_status
        if not self.status_only:
          self.server_status.update({'error':False, 'restart':False, 'reboot':False,\
                'shutdown':False, 'error_msg':None})

        self.command_dict = self.default_command_dict

        if command_dict is not None:
           self.command_dict = command_dict

        if not self.status_only:
          if SHUTDOWN_COMMAND not in self.command_dict:
              self.command_dict[SHUTDOWN_COMMAND]=\
                {'arg_name_list':[], 'comment':'shut down camera controller and exit server'}

          if RESTART_COMMAND not in self.command_dict:
              self.command_dict[RESTART_COMMAND]=\
                {'arg_name_list':[], 'comment':'restart camera control program'}

          if REBOOT_COMMAND not in self.command_dict:
              self.command_dict[REBOOT_COMMAND]=\
                {'arg_name_list':[], 'comment':'reboot controller and restart camera control program'}

        self.done_reply = DONE_REPLY
        self.error_reply = ERROR_REPLY
        if done_reply is not None:
           self.done_reply = done_reply
        if error_reply is not None:
           self.erro_reply = error_reply
       
        assert host is not None, "unspecified host name for socket connections"
        self.host = host

        assert command_fnc is not None, "unspecified command function"
        self.command_fnc = command_fnc

        if port is not None:
           self.port = port

        if maxbufsize is not None:
           self.maxbufsize = maxbufsize

        if timeout is not None:
           self.timeout = timeout

        if logger is not None:
           self.logger = logger
        else:
           self.logger = LS4_Logger(name="LS4_Command_Stream")

        self.info = self.logger.info 
        self.debug = self.logger.debug
        self.warn  = self.logger.warn
        self.error= self.logger.error
        self.critical= self.logger.critical

        self.command_prev=""
        self.arg_value_list_prev = ""
        self.reply_prev=""
        self.error_prev=False
        self.error_msg_prev=False

    async def run(self):

        self.debug("opening socket connection on host %s port %d" %\
             (self.host,self.port))
       
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))  

        self.debug("listening on port %d" % self.port)
        server_socket.listen(self.max_connections)
        self.debug("polling connections on port %d" % self.port)
        poller = select.poll()
        poller.register(server_socket, select.POLLIN)

        await asyncio.sleep(5)
        # Create a dictionary to store client sockets
        client_sockets = {}
        while not (self.server_status.get('shutdown') or self.server_status.get('restart') or\
              self.server_status.get('reboot') or self.ls4_abort.abort_server):

          await asyncio.sleep(0.1)
          events = poller.poll(self.polling_timeout)  # Timeout of 1 second
          client_socket=None
          client_address =None

          for fd, event in events:
            reply = None
            if fd == server_socket.fileno():
              self.debug("new server connection on port %d" % self.port)
              client_socket, client_address = server_socket.accept()
              self.debug("accepting connection on port %d" % self.port)
              #self.debug("accepted connection from %s" % client_address)
              client_sockets[client_socket.fileno()] = client_socket
              self.debug("registering new client connections for polling on port %d" % self.port)
              poller.register(client_socket, select.POLLIN)
            else:
              #self.debug("reading commands from %s" % client_address)
              # get data from an existing client
              client_socket = client_sockets[fd]
              # Keep reading commands from the open socket until it closes
              connection_open = True
              while connection_open and not self.ls4_abort.abort_server:
                command = client_socket.recv(self.maxbufsize).decode()
                command=command.strip()
                self.debug("port %d, command is : %s" % (self.port,command))
                if not command:
                    #print("client %s disconnected" % client_address)
                    connection_open=False
                    poller.unregister(client_socket)
                    client_socket.close()
                    del client_sockets[fd]
                else:
                    reply = None
                    reply_list=[reply]
                    self.debug("port %d, handling command: %s" % (self.port,command))
                    await self.handle_command(command,reply_list)
                    self.debug("port %d, done handling command: [%s]  reply: [%s]" % \
                            (self.port,command,reply_list[0]))
                    reply = reply_list[0].strip()
                    #while len(reply) < 256:
                    #    reply = reply + " "
                    reply = reply + "\n"
                    reply = reply.encode()
                    self.debug("port %d, sending reply: %s" % (self.port,reply))
                    try:
                      #client_socket.send(reply)
                      client_socket.sendall(reply)
                    except Exception as e:
                      self.error("port %d, exception sending reply [%s]: %s" % (self.port,reply,e))
                    self.debug("done sending reply: %s" % reply)
                await asyncio.sleep(0.1)
                self.ls4_abort.check_abort()
         
              self.debug("closing connection on port %d" % self.port)
              client_socket.close()

          self.ls4_abort.check_abort()
         
        if self.ls4_abort.abort_server:
           self.server_status.update({'abort':True})
           self.warn("command server aborted")
           #self.ls4_abort.clear_server_abort()

        self.ls4_abort.shutdown()

    def check_command(self,command_str=None):

        error_msg = ""
        warn_msg = ""
        shutdown_flag=False
        restart_flag=False
        reboot_flag=False
        error_flag=False

        command_list = command_str.split()
        command = command_list[0]
        arg_value_list = command_list[1:]

        # if a list of words appears in the arg_value_list, and these
        # list entries are bracketed by list element "'",
        # then these list entries were originally split up from a string argument to
        # the command (probably the "header" command).
        # Join the words back into the original string argument, 
        # and adjust the arg_value_list so that the string argument
        # appears as a single entry:
        # E.G. if arg_value_list =
        #       ["a", "b". "c", "'",  "I", "am", "a", "string, "'", "d"]
        # then change it to"
        #       ["a", "b". "c", "I am  a string", "d"]
        # ending with "'". Count all these entries as one arg

        new_arg_list = []
        if "'" in arg_value_list:
          string_arg = ""
          # determine values index1,i1,index2,i2 such that
          #   string_arg = the concatenation of arg_value_list[i1:i2]
          # and
          #   new arg_arg_list = arg_value_list[0:index1] + [string_arg] + arg_values_list[index2:]
          #
          # set index1 to the index of the first instance of "'" in the arg list
          index1 = arg_value_list.index("'")
          #
          # initialize new arg list with elements from the original arg list preceding the first "'"
          new_arg_list = arg_value_list[0:index1]

          # initialize list of words (l) to go into string
          i1 = index1 + 1
          l = arg_value_list[i1:]

          # check that a second instance of "'" appears in list l. If not, record and error
          if "'" in l: 

            #set index to the index of the first  instance of "'" in list l.
            index = l.index("'")

            # join all the elements  in list l from 0 to index into string_arg
            string_arg  = " ".join(l[0:index])

            # set index2 to the index within arg_val_list of the second instance of "'" in the arg list
            index2 = i1 + l.index("'")

            # finally set new arg list to the elements from arg_value_list preceding the first "'",
            # followed by string_arg, and ending with all the elements from arg_value_list succeeding
            # the second "'".
            # 
            i2 = index2 + 1
            new_arg_list = arg_value_list[0:index1] + [string_arg] + arg_value_list[i2:]    
            self.debug("orginal arg_value_list: %s" % str(arg_value_list))
            self.debug("new arg_value_list: %s" % str(new_arg_list))
            arg_value_list = new_arg_list
          else:
            error_msg="argument has unterminated string: command [%s], args[%s], expected [%s]" %\
                     (command,str(arg_value_list),str(self.command_dict[command]['arg_name_list']))
            error_flag = True

        n_args = len(arg_value_list) 
          

        if error_flag:
           self.error(error_msg)

        elif command not in self.command_dict:
           warn_msg = "invalid command: %s" % str(command_list)
           self.error(warn_msg)
           error_flag=True

        elif n_args  != len(self.command_dict[command]['arg_name_list']):
           error_msg="incorrect args: command [%s], args[%s], expected [%s]" %\
                     (command,str(arg_value_list),str(self.command_dict[command]['arg_name_list']))
           self.error(error_msg)
           error_flag=True

        elif (command == SHUTDOWN_COMMAND) and not self.status_only:
           self.debug("shutdown command received")
           shutdown_flag = True

        elif (command == RESTART_COMMAND) and not self.status_only:
           self.debug("restart command received")
           restart_flag = True

        elif (command == REBOOT_COMMAND) and not self.status_only:
           self.debug("reboot command received")
           reboot_flag = True

        return command,arg_value_list,shutdown_flag,restart_flag,reboot_flag,error_flag,error_msg

    async def handle_command(self,command_str=None,reply_list=None):
        """ execute the command. Return with reply """

        reply_list[0] = self.done_reply
        error_msg = None

        shutdown_flag=False;
        restart_flag=False;
        reboot_flag=False;
        error_flag=False
        command,arg_value_list,shutdown_flag,restart_flag,reboot_flag,error_flag,error_msg =\
                    self.check_command(command_str)
       
        if not self.status_only:
          self.server_status.update(\
            {'error':error_flag,'restart':restart_flag,'reboot':reboot_flag,\
             'shutdown':shutdown_flag,'error_msg':error_msg})

          if command in ["status","help"]  :
            self.server_status.update({'command':self.command_prev,'arg_value_list':self.arg_value_list_prev,\
                'reply':self.reply_prev,'error':self.error_prev,'error_msg':self.error_msg_prev})
          else:
            self.server_status.update({'command':command,'arg_value_list':arg_value_list,'reply':''})
            self.command_prev=command
            self.arg_value_list_prev = arg_value_list
            self.reply_prev = ''
            self.error_prev = error_flag 
            self.error_msg_prev = error_msg 
            

        if error_flag:
           if error_msg is None:
              error_msg = "check_command returns error"
           self.warn(error_msg)
           reply_list[0] = self.error_reply + " " + error_msg

        elif not (shutdown_flag or restart_flag or reboot_flag):


           self.debug("calling command_fnc with command %s and args %s" %\
                    (command,arg_value_list))
           await self.command_fnc(command=command,arg_value_list=arg_value_list,reply_list=reply_list)
           self.debug("done calling command_fnc with command [%s]  args [%s] and reply [%s]" %\
                    (command,str(arg_value_list),reply_list[0]))
        

      
        # for non-status command:
        #   if command reply is None, set reply to self.error_reply + error message.
        #   Otherwise, do not change the reply. 
        #   In either case, update the server_status with the respective reply and
        #   record the reply in reply_prev.
        #
        # for status command:
        #   if successful, append the reply with the server status.
        #   otherwise, do nothing and do not record the reply in reply_prev.

        if command not in ['status','help']:
          if reply_list[0] is None:
            error_msg="command_fnc reply is None"
            reply_list[0]=self.error_reply + " " + error_msg
            self.server_status.update({'error':True, 'error_msg':error_msg})

          self.server_status.update({'reply':reply_list[0]})
          self.reply_prev = reply_list[0]

        elif command == 'status' and DONE_REPLY in reply_list[0]:

          # add additional status words from server_status to reply
          aux_reply = reply_list[0].replace("}","")

          for key in ['error','error_msg','command','arg_value_list','reply']:
             status = self.server_status.get()
             if key in status:
               k1= "'"+"cmd_"+key+"'"
               if key in ['error','arg_name_list']:
                  val=str(status[key])
                  self.debug("server status: [%s:%s] val:%s" % (key,status[key],val))
               else:
                  val="'"+str(status[key])+"'"
               aux_reply += "," + " " + k1 + ":" + val

          reply_list[0] = aux_reply

