# -*- coding: utf-8 -*-
#
#
# @Author: David Rabinowitz (david.rabinowitz@yale.edu)
# @Date: 2024-03-06
# @Filename: ls4_controller.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
#
#
# This is an extension of the controller.py in sdss-archon
# distribution (on github)
#
# 
# LS4_SyncIO is class to facility  synchronous communications with multiple
# Archon controllers ( specifically "send_command" and "set_param" )

import asyncio
from archon import log
from archon.ls4.ls4_events  import *

from . import FOLLOWER_TIMEOUT_MSEC

class LS4_SyncIO():

    def __init__(self,name=None, param_args=None, command_args=None):

        self.name=name
        self.info=log.info
        self.debug=log.debug
        self.warn=log.warn
        self.error=log.error

        self.param_sync_msg_list = None
        self.param_sync_reply_list = None
        self.command_sync_msg_list = None
        self.command_sync_reply_list = None
        self.leader = False # update to True for the controllers assigned to lead
        self.follower_timeout_msec = FOLLOWER_TIMEOUT_MSEC
        self.num_controllers = 0
        self.sync_index = None
        self.prefix = "follower %s:" % self.name # update in set_leader

        # sync_flag is set when parameters must be synchronously set
        # across controllers. That is when the sync_event 
        # object comes into play (see self.sync_set_param() below).

        self.sync_flag = False

        # sync_test is set to True when sync_test is being execute
        self.sync_test = False
        
        # global variables to save parameter and command args for sync_set_param()
        # and sync_send_command. 
        # These allows concurrent asyncio processes to verify they are setting
        # the same parameter or sending the same command at the same time

        self.param_args=param_args
        self.command_args=command_args

    def add_loggers(self,info=None,debug=None,error=None,warn=None):

        if info is not None:
           self.info = info
        if debug is not None:
           self.debug= debug
        if warn is not None:
           self.warn = warn
        if error is not None:
           self.error = error
       

    def sync_log(self,str):
        if self.sync_test:
           self.debug(str)
           #self.info(str)
        else:
           self.debug(str)
           #self.info(str)

    def set_sync_event_lists(self,param_sync_msg_list: list[asyncio.Event] = [],\
                     param_sync_reply_list: list[asyncio.Event] = [],
                     command_sync_msg_list: list[asyncio.Event] = [],
                     command_sync_reply_list: list[asyncio.Event] = []):
         self.param_sync_msg_list=param_sync_msg_list
         self.param_sync_reply_list=param_sync_reply_list
         self.command_sync_msg_list=command_sync_msg_list
         self.command_sync_reply_list=command_sync_reply_list

    def set_sync_index(self,sync_index: int):
         self.sync_index = sync_index

    def set_lead(self, lead_flag: bool = False):
         self.leader = lead_flag 
         self.prefix = "leader %s:" % self.name

    def set_sync(self, sync_flag: bool = False):
        self.sync_flag = sync_flag

    def set_num_controllers(self, num_controllers = 0):
        self.num_controllers = num_controllers

    async def sync_prepare(self,param_args=None,command_args=None):
 
        """ prepare for synchronous execution of set_param or send_command function 

            leader:   check that events are clear,
                      update global copies of param or command args

            follower: wait for msg_event, 
                      verify param or command args match global copy,
                      clear msg_event
        """

        error_msg = None
        prefix = self.prefix
        self.sync_test = False
        param_flag = False

        self.sync_log("%s: preparing for synchronous IO" % prefix)

        assert [command_args,param_args] != [None,None], "neither param or command args specified"
        assert command_args is None or param_args is None, "both param and command args specified"

        if param_args is not None:
           param_flag=True
           sync_msg_list = self.param_sync_msg_list
           sync_reply_list = self.param_sync_reply_list
           prefix = "param " + prefix
        else:
           param_flag=False
           sync_msg_list = self.command_sync_msg_list
           sync_reply_list = self.command_sync_reply_list
           prefix = "command " + prefix

        if self.leader:

           # make sure the events in param_sync_msg_list are initially clear
           result = await check_events(event_list=sync_msg_list, sync_index=-1,set_flag = False)
           if result is False:
              error_msg = "%s: not all sync_msg events are initially clear" % prefix

           # make sure the events in param_sync_reply_list are initially clear
           else:
             result = await check_events(event_list=sync_reply_list, sync_index=-1,set_flag = False)
             if result is False:
                error_msg =  "%s: not all sync_reply events are initially clear" % prefix

           # update global copies of param_args and/or command_args
           if param_flag:
             self.param_args[0]={}
             self.param_args[0].update(param_args)
             if param_args['param'] in ["SYNCTEST","synctest","SYNC_TEST","sync_test"]:
                self.sync_test = True
           else:
             self.command_args[0]={}
             self.command_args[0].update(command_args)

        # follower
        else:

           self.sync_log("%s waiting for sync_msg event: sync_index %d" % (prefix,self.sync_index))
           await wait_events(event_list=sync_msg_list,sync_index = self.sync_index)

           # the follower checks that the param or command arguments match the global values
           if param_flag:
              if param_args != self.param_args[0]:
                  error_msg = "%s param_args mismatch: local : %s, global: %s" %\
                   (prefix,param_args,self.param_args[0])
           else:
               if command_args != self.command_args[0]:
                  error_msg = "%s command_args mismatch: local : %s, global: %s" %\
                    (prefix,command_args,self.command_args[0])

           self.sync_log("%s clearing sync_msg events: sync_index %d" % (prefix,self.sync_index))
           await clear_events(event_list=sync_msg_list,sync_index=self.sync_index)


        if error_msg is not None:
           self.error("%s: %s" % (prefix,error_msg))
           raise ArchonControllerError(f"Failed preparing sync: %s" % error_msg)
      
        self.sync_log("%s: done preparing for synchronous IO" % prefix)

    async def sync_update(self,param_flag=None,command_flag=None):
 
        """ update synchronous execution of set_param or send_command function    

            leader   : set sync_msg events to alert followers,
                       wait for sync_reply events from followers
                       clear sync_reply events
        
            follower : set sync_reply event to alert leader

        """

        error_msg = None
        prefix = self.prefix

        assert [command_flag,param_flag] != [None,None], "neither param nor command flag specified"
        assert command_flag is None or param_args is None, "both param and command flag specified"

        if param_flag:
           sync_msg_list = self.param_sync_msg_list
           sync_reply_list = self.param_sync_reply_list
           prefix = "param " + prefix
        else:
           sync_msg_list = self.command_sync_msg_list
           sync_reply_list = self.command_sync_reply_list
           prefix = "command " + prefix

        if self.leader :
           self.sync_log("%s setting sync_msg_events: sync_index %d" % (prefix,-1))
           result = await set_events(event_list=sync_msg_list,sync_index=-1)
           self.sync_log("%s result of setting sync_msg_events: %s" % (prefix,result))

           # wait here for the followers to set the sync reply events
           self.sync_log("%s waiting for sync_reply events to set: sync_index = %d" % (prefix,-1))
           result=await wait_events(event_list=sync_reply_list,sync_index=-1)
           self.sync_log("%s result of waiting sync_reply_events: %s" % (prefix,result))

           self.sync_log("%s clearing sync_reply events: sync_index %d" % (prefix,-1))
           await clear_events(event_list=sync_reply_list, sync_index=-1)

        else:

           self.sync_log("%s setting sync_reply_events: sync_index %d" % (prefix,self.sync_index))
           result = await set_events(event_list=sync_reply_list,sync_index=self.sync_index)
           self.sync_log("%s result of setting sync_reply_events: %s" % (prefix,result))
           

        if error_msg is not None:
           self.error("%s: %s" % (prefix,error_msg))
           raise ArchonControllerError(f"Failed updating sync: %s" % error_msg)


    async def sync_verify(self,command_flag=None,param_flag=None):
 
        """ check synchronization of leader controller with followers

            leader  :  set sync msg events
                       wait for sync replies
                       clear sync replies

            follower:  wait for sync msg events
                       clear sync msg events
                       send sync replies
        """

        error_msg = None
        prefix = self.prefix
        assert [command_flag,param_flag] != [None,None], "neither param nor command flag specified"
        assert command_flag is None or param_args is None, "both param and command flag specified"

        if param_flag:
           sync_msg_list = self.param_sync_msg_list
           sync_reply_list = self.param_sync_reply_list
           prefix = "param " + prefix
        else:
           sync_msg_list = self.command_sync_msg_list
           sync_reply_list = self.command_sync_reply_list
           prefix = "command " + prefix


        if self.leader and error_msg is None:
           self.sync_log("%s setting sync_msg_events: sync_index %d" % (prefix,-1))
           result = await set_events(event_list=sync_msg_list,sync_index=-1)
           self.sync_log("%s result of setting sync_msg_events: %s" % (prefix,result))

           # wait here for the followers to set the sync reply events
           self.sync_log("%s waiting for sync_reply events to set: sync_index %d" % (prefix,-1))
           await wait_events(event_list=sync_reply_list,sync_index=-1)
           self.sync_log("%s done waiting for sync_reply events to set" % prefix)

           self.sync_log("%s clearing sync_reply events: sync_index %d" % (prefix,-1))
           await clear_events(event_list=sync_reply_list, sync_index=-1)


        elif error_msg is None:
           self.sync_log("%s waiting for sync_msg event: sync_index %d" % (prefix,self.sync_index))
           await wait_events(event_list=sync_msg_list,sync_index = self.sync_index)

           self.sync_log("%s clearing sync_msg events: sync_index %d" % (prefix,self.sync_index))
           await clear_events(event_list=sync_msg_list,sync_index=self.sync_index)

           self.sync_log("%s setting sync_reply_events: sync_index %d" % (prefix,self.sync_index))
           result = await set_events(event_list=sync_reply_list,sync_index=self.sync_index)
           self.sync_log("%s result of setting sync_reply_events: %s" % (prefix,result))
           

        if error_msg is not None:
           self.error("%s: %s" % (prefix,error_msg))
           raise ArchonControllerError(f"Failed verifying sync: %s" % error_msg)

