import asyncio

from archon.controller.ls4_controller import LS4Controller
from archon.controller.ls4_logger import LS4_Logger
from archon.ls4.ls4_events import LS4_Events

from archon import log

class LS4_Sync():

    """ 
        class to synchronously set a controller parameter in the leader and follower controllers.
        When controllers are following a lead controller, a parameter can be set synchronously
        if all controllers first execute the PREPPARAM or FASTPREPPARAM command. After that,
        the next parameter set by the leader using LOADPARAM or FASTLOADPARAM is synchronously
        set by the leader and followers.

        To coordinate these actions, the Sync_Param class initializes 
        an separate instance of the asyncio Event synchronizer for each controller.
        As new controller are instantiated externally, they are added to a list of controllers to
        be synchronously operated.
      
        Member function "set_param(param,value)" uses the "asyncio.gather()" function to synchronously
        run the "LS4Controller.set_param(index,param_value)" for all the controllers.

       
    """

    def __init__(
        self,
        num_synced_controllers: int = 0 ,
        lead_index: int = 0,
        ls4_logger: LS4_Logger | None = None
    ):
     
        assert lead_index is not None, "lead_index must be specified"
        assert num_synced_controllers > 0, "num_synced_controllers must exceed 0"
        assert lead_index in range(0,num_synced_controllers), \
                  "lead_index must be in range 0 to %d" % num_synced_controllers

        if ls4_logger is None:
           self.ls4_logger = LS4_Logger()
        else:
           self.ls4_logger=ls4_logger

        self.info = self.ls4_logger.info
        self.debug = self.ls4_logger.debug
        self.warn= self.ls4_logger.warn
        self.error= self.ls4_logger.error
        self.critical= self.ls4_logger.critical

        # list of instances of LS4Controller, one for each synchronized controller
        self.synced_controller_list=[]

        # total number of synced controllers
        self.num_synced_controllers = num_synced_controllers
        
        #index within synced_controller_list of the lead controller
        self.lead_index = lead_index

        # lists of asyncio Events, one for each controller:
        #
        # setting params:
        # param_sync_msg_list is used by the lead controller to signal followers
        # param_sync_reply_list is used by the followers to signal the lead
        #
        # sending commands:
        # command_sync_msg_list is used by the lead controller to signal followers
        # command_sync_reply_list is used by the followers to signal the lead
        #
        self.param_sync_msg_list = []
        self.param_sync_reply_list = []
        self.command_sync_msg_list = []
        self.command_sync_reply_list = []

        for index in range(0,self.num_synced_controllers):
           if index != lead_index:
             self.param_sync_msg_list.append(asyncio.Event())
             self.param_sync_reply_list.append(asyncio.Event())
             self.command_sync_msg_list.append(asyncio.Event())
             self.command_sync_reply_list.append(asyncio.Event())

        self.event_lists={\
            "param_msg":self.param_sync_msg_list,
            "param_reply":self.param_sync_reply_list,
            "command_msg":self.command_sync_msg_list,
            "command_reply":self.command_sync_reply_list}


        # ls4_events keeps track of event list for synchronizing controller threads
        self.ls4_events=LS4_Events(event_lists=self.event_lists, ls4_logger = self.ls4_logger)


        #global copy of arguments used by ls4_controller.set_params
        self.param_args = [{}]
        self.command_args = [{}]

    def add_controller(
        self,
        controller: LS4Controller = None,
        sync_index: int | None = None
    ):

        """ add a controller to the list of synchronized controllers.
            Also set the sync_msg_list and sync_reply_list for each
            controller.
        """

        assert controller is not None, "controller is not instantiated"       

        self.synced_controller_list.append(controller)
       
        """
        controller.set_sync_event_lists(\
                      param_sync_msg_list=self.param_sync_msg_list,
                      param_sync_reply_list=self.param_sync_reply_list,
                      command_sync_msg_list=self.command_sync_msg_list,
                      command_sync_reply_list=self.command_sync_reply_list)
        """
        controller.set_sync_index(sync_index)


    async def set_sync(self,sync_flag = False):

        """If sync_flag is True/False, enable/disable synchronization of the controllers."""

        result = await self.ls4_events.check_all_events_clear()
        assert result is True,"not all sync events are clear"

        for controller in self.synced_controller_list:
            controller.set_sync(sync_flag)

    async def test_sync(
        self,
    ):

        """ check that the semaphores properly synchronize by synchronously setting
            a NOP parameter. No parameter is actually set by the controllers, but 
            the semaphores are used to coordinate the actions of the controllers in
            the same way
        """

        #print("running set_param with sync_test = True")
        try:
          await self.set_param(param="SYNCTEST",value=0)
        except Exception as e:
          error_msg = "Exception testing sync by setting SYNCTEST param to 0: %s" % e
          self.error(error_msg)
          raise RuntimeError(error_msg)
         
        #print("done running set_param with sync_test = True")

    async def set_param(
        self,
        param: str = None, 
        value: int = None, 
        force: bool = False,
    ):

        """ set a parameter synchronously among controller cabled together to allow
            synchronous operation.
            
        """

        self.debug("num_synced_controllers = %d" % self.num_synced_controllers)
        self.debug("length of synced_controller_list = %d" % len(self.synced_controller_list))
        try:
          await asyncio.gather(*(self.synced_controller_list[index].set_param(param=param,\
                            value=value) for index in range(0,self.num_synced_controllers)))

        except Exception as e:
          error_msg = "Exception setting param %s to %d: %e" % (param,value,e)
          self.error(error_msg)
          raise RuntimeError(error_msg)
