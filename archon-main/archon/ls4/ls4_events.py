import asyncio
from archon import log
from archon.controller.ls4_logger import LS4_Logger

# utility functions for working with asyncio Events
# The LS4_Events class is specifically used to synchronize calls to
# set_param() and send_command() by ls4_controller.py

class LS4_Events():

    def __init__(self,
        #num_controllers: int,
        event_lists: dict | None = None,
        ls4_logger: LS4_Logger | None = None
    ):

        if ls4_logger is None:
           self.ls4_logger = LS4_Logger()
        else:
           self.ls4_logger=ls4_logger

        self.info = self.ls4_logger.info
        self.debug = self.ls4_logger.debug
        self.warn= self.ls4_logger.warn
        self.error= self.ls4_logger.error
        self.critical= self.ls4_logger.critical

        #self.num_controllers = num_controllers

        assert event_lists is not None, "event_lists are unspecified"
        self.event_lists = event_lists
        self.num_synced_controllers = len(event_lists)
        param_msg_list = None
        param_reply_list = None
        command_msg_list = None
        command_reply_list = None

        if 'param_msg' in event_lists:
            param_msg_list = event_lists['param_msg']
        if 'param_reply' in event_lists:
            param_reply_list = event_lists['param_reply']
        if 'command_msg' in event_lists:
            command_msg_list = event_lists['command_msg']
        if 'command_reply' in event_lists:
            command_reply_list = event_lists['command_reply']

        assert param_msg_list is not None, "param_msg_list is unspecified in event_list"
        assert param_reply_list is not None, "param_reply_list is unspecified in event_list"
        assert command_msg_list is not None, "command_msg_list is unspecified in event_list"
        assert command_reply_list is not None, "command_reply_list is unspecified in event_list"

        self.param_msg_list = param_msg_list
        self.param_reply_list = param_reply_list
        self.command_msg_list = command_msg_list
        self.command_reply_list = command_reply_list

    async def check_all_events_clear(self):

        all_results = True

        #check that param_sync_msg events are all clear
        result = await self.check_events(event_list=self.param_msg_list,sync_index=-1,set_flag=False)
        if  not result:
            all_results = False
            self.warn("not all param msg events are clear")

        #check that param_sync_reply events are all clear
        result = await self.check_events(event_list=self.param_reply_list,sync_index=-1,set_flag=False)
        if  not result:
            all_results = False
            self.warn("not all param reply events are clear")

        #check that command_sync_msg events are all clear
        result = await self.check_events(event_list=self.command_msg_list,sync_index=-1,set_flag=False)
        if  not result:
            all_results = False
            self.warn("not all command msg events are clear")

        #check that command_sync_reply events are all clear
        result = await self.check_events(event_list=self.command_reply_list,sync_index=-1,set_flag=False)
        if  not result:
            all_results = False
            self.warn("not all command reply events are clear")

        return all_results

    async def wait_events(self,
        event_list: list[asyncio.Event]=[],
        sync_index: int = -1,
    ):
        """ wait for  for all (sync_index-1) or a particular (sync_index>-1) 
            event in event_list to be set
        """

        assert sync_index in range(-1,len(event_list)),\
                "sync_index [%d] out of range [-1 to %d]" % (sync_index,len(event_list))

        if sync_index > -1:
           #log.debug("wating for event for sync index %d" % sync_index)
           result = await self.event_action(event_list[sync_index],"wait")
           return [result]
        else:
           result = await asyncio.gather(*(self.event_action(event,"wait") for event in event_list))
           #log.debug("wait_events: result = %s" % result)
           return result


    async def check_events(self,
        event_list: list[asyncio.Event]=[],
        sync_index: int = -1,
        set_flag: bool = True
    ):

        """ check that all (sync_index==-1) or a specific event  (sync_index>-1) in event_list 
            have status matching set_flag 
        """
        assert sync_index in range(-1,len(event_list)),\
                "sync_index [%d] out of range [-1 to %d]" % (sync_index,len(event_list))

        index = 0
        all_correct = True
        
        if sync_index > -1:
           #log.debug("checking event for sync index %d" % sync_index)
           if event_list[sync_index].is_set() != set_flag:
             all_correct = False
        else:
           result = await asyncio.gather(*(self.event_action(event,"is_set") for event in event_list))
           """
           result = []
           index = 0
           for event in event_list:
              r = event.is_set()
              log.debug("event %d state: %s" % (index,r))
              result.append(r)
           """
           if (not set_flag)  in result:
              #log.debug ("check_events unwanted result (all should be %s) : %s" % (set_flag,result))
              all_correct = False

        return all_correct

    async def set_events(self,
        event_list: list[asyncio.Event]=[],
        sync_index: int = -1 
    ):

        """ set  all (sync_index==1) or a specific event  (sync_index>-1) in event_list """

        assert sync_index in range(-1,len(event_list)),\
                "sync_index [%d] out of range [-1 to %d]" % (sync_index,len(event_list))

        if sync_index > -1:
           #log.debug("setting event for sync index %d" % sync_index)
           result = await self.event_action(event_list[sync_index],"set")
           results = [result]
        else:
           result = await asyncio.gather(*(self.event_action(event,"set") for event in event_list))
           return result


    async def clear_events(self,
        event_list: list[asyncio.Event]=[],
        sync_index: int = -1 
    ):
        """ clear all (sync_index==1) or a specific event  (sync_index>-1) in event_list """
        

        assert sync_index in range(-1,len(event_list)),\
                "sync_index [%d] out of range [-1 to %d]" % (sync_index,len(event_list))

        if sync_index > -1:
           #log.debug("clearing event for sync index %d" % sync_index)
           result = event_list[sync_index].clear()
           return [result]

        else:
           result = await asyncio.gather(*(self.event_action(event,"clear") for event in event_list))
           """
           result=[]
           index = 0
           for event in event_list:
               log.debug("clearing event %d" % index)
               result.append(event.clear())
               log.debug("result of clearing: %s" % event.is_set())
           """
           #log.debug("clear_events result: %s" % result)

           return result

    async def event_action(self,
        event: asyncio.Event,
        action: str = "none"
    ):
        result = None

        assert action in ["set","clear","is_set","wait"],\
           "unexpected action: %s" % action

        if action == "set":
           result = event.set()
        elif action == "clear":
           result = event.clear()
        elif action == "is_set":
           result = event.is_set()
        elif action == "wait":
           result = await event.wait()
        return result


