# define LS4_Command_Server class.

# This is a creates a basic TCP server to receive commands, execute them, and return
# a reply


import sys
import os
import socket
import asyncio
#import logging
from archon.controller.ls4_logger import LS4_Logger   
from . import DEFAULT_PORT, DEFAULT_MAXBUFSIZE, DEFAULT_TIMEOUT,\
              DONE_REPLY, ERROR_REPLY, SHUTDOWN_COMMAND, RESTART_COMMAND

class LS4_Command_Server():

    """ Class to manage command server for LS4_Control_Program """

    # recognized camera commands
    default_command_dict={\
        'init':{'args':[],'comment':'initialize camera controller'},\
        'open shutter':{'args':[],'comment':'open the camera shutter'},\
        'close shutter':{'args':[],'comment':'close the camera shutter'},\
        'status':{'args':[],'comment':'return camera status'},\
        'clear':{'args':[],'comment':'clear the camera'},\
        'r':{'args':['num_lines','file_root'],\
             'comment':'readout num_lines from camera and write to file'},\
        'h':{'args':['key_word','value'],\
             'comment':'add keyword/value to image fits header'},\
        'e':{'args':['shutter','exptime','fileroot'],\
            'comment':' expose for exptime sec with shutter open (True,False) and savee file'}\
        }

    async def default_command_function(self,command=None,command_args=None,reply_list=None):

        self.info("inside command function")

        if command is not None:
           self.info("command_function: command and args are [%s] [%s]" %\
                     (command,str(command_args)) )

        reply_list[0] = DONE_REPLY
        self.info("command_function: reply is %s" % reply_list[0])


    def __init__(self,host=None,port=None,maxbufsize=None,timeout=None, \
                 command_fnc=None, logger=None, command_dict=None,\
                 done_reply=DONE_REPLY,error_reply=ERROR_REPLY):

        """
        Specify host name, TCP port, maximum buffer size, command timeout (sec), function to
        process commands, logger , dictionary of commands, and expected replies from the command
        function when successful (done_reply) or when there is an error (error_reply).
        
        The logger  must provide functions info,warn,error,debug, and critical.
       
        The command dictionary supplies all possible commands as keys to the dictionary, with
        each key associated with a description of the command. Each description is of the form
        {'args':arg_list;'comment':comment_string}, where arg_list is the list of argument
        names (an empty list if there are no arguments), and comment_string  explains what
        the command is for.
       
        The command function must expect three arguments: 
          command: the command name (the keys in the command dictionary)
        
          command_args: a list of the values provided for the arguments, in the order in which they
           appear in the command dictionary.
        
          reply_string: a list whose only member is a placeholder for command reply.
        
        The reply string must begin with done_reply or error_reply  followed
        by an optional string with additional explanation.
        """        

        self.port = DEFAULT_PORT
        self.timeout = DEFAULT_TIMEOUT
        self.maxbufsize = DEFAULT_MAXBUFSIZE
        self.command_fnc = self.default_command_function
        self.server_status={'error':False, 'restart':False, 'shutdown':False, 'error_msg':None}

        self.command_dict = self.default_command_dict

        if command_dict is not None:
           self.command_dict = command_dict

        if SHUTDOWN_COMMAND not in self.command_dict:
              self.command_dict[SHUTDOWN_COMMAND]=\
                {'args':[], 'comment':'shut down camera controller and exit server'}

        if RESTART_COMMAND not in self.command_dict:
              self.command_dict[RESTART_COMMAND]=\
                {'args':[], 'comment':'restart camera control program'}

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

    async def run(self):

        self.debug("opening socket connection on host %s port %d" %\
             (self.host,self.port))
        server_socket = socket.socket()  
        server_socket.bind((self.host, self.port))  
        reply = None

        while not self.server_status['shutdown'] and not self.server_status['restart']:
          self.debug("listening")
          server_socket.listen(2)
          conn, address = server_socket.accept()  # accept new connection
          self.debug("Connection from: " + str(address))
          connection_open = True
          while connection_open:
            command = conn.recv(self.maxbufsize).decode()
            command=command.strip()
            self.debug("command is : %s" % command)
            if not command:
                # if data is not received break
                connection_open=False
            else:
                reply = None
                reply_list=[reply]
                self.debug("handling command: %s" % command)
                await self.handle_command(command,reply_list)
                self.debug("done handling command: [%s]  reply: [%s]" % (command,reply_list[0]))
                reply = reply_list[0].strip()
                reply = reply + "\n"
                reply = reply.encode()
                self.debug("sending reply: %s" % reply)
                try:
                  conn.send(reply)
                except Exception as e:
                  self.error("exception sending reply [%s]: %s" % (reply,e))
                self.debug("done sending reply: %s" % reply)
          self.debug("closing connection")
          conn.close()

    def check_command(self,command_str=None):

        command_list = command_str.split()
        command = command_list[0]
        command_args = command_list[1:]
        error_msg = ""
        warn_msg = ""
        shutdown_flag=False
        restart_flag=False
        error_flag=False

        if command not in self.command_dict:
           warn_msg = "invalid command: %s" % str(command_list)
           self.warn(warn_msg)

        elif len(command_args) != len(self.command_dict[command]['args']):
           error_msg="incorrect args: command [%s], args[%s], expected [%s]" %\
                     (command,str(command_args),str(self.command_dict[command]['args']))
           self.error(error_msg)
           error_flag=True

        elif command == SHUTDOWN_COMMAND:
           self.debug("shutdown command received")
           shutdown_flag = True

        elif command == RESTART_COMMAND:
           self.debug("restart command received")
           restart_flag = True

        return command,command_args,shutdown_flag,restart_flag,error_flag,error_msg

    async def handle_command(self,command_str=None,reply_list=None):
        """ execute the command. Return with reply """

        reply_list[0] = self.done_reply
        error_msg = None

        shutdown_flag=False;
        restart_flag=False;
        error_flag=False
        command,command_args,shutdown_flag,restart_flag,error_flag,error_msg = self.check_command(command_str)

        self.server_status={'error':error_flag,'restart':restart_flag,'shutdown':shutdown_flag,'error_msg':error_msg}
        if error_flag:
           if error_msg is None:
              error_msg = "check_command returns error"
           self.warn(error_msg)
           reply_list[0] = self.error_reply + " " + error_msg

        elif not shutdown_flag and not restart_flag:

           self.debug("calling command_fnc with command %s and args %s" %\
                    (command,str(command_args)))
           await self.command_fnc(command=command,command_args=command_args,reply_list=reply_list)
           self.debug("done calling command_fnc with command [%s]  args [%s] and reply [%s]" %\
                    (command,str(command_args),reply_list[0]))
        

        if reply_list[0] is None:
          error_msg="command_fnc reply is None"
          self.server_status['error']=True
          self.server_status['error_msg']=error_msg
          reply_list[0]=self.error_reply + " " + error_msg

