import asyncio

from archon.ls4.ls4_controller import LS4Controller

class LS4_Sync():

    """ 
        class to synchronously set a controller parameter in the leader and follower controllers.
        When controllers are following a lead controller, a parameter can be set synchronously
        if all controllers first execute the PREPPARAM or FASTPREPPARAM command. After that,
        the next parameter set by the leader using LOADPARAM or FASTLOADPARAM is synchronously
        set by the leader and followers.

        To coordinate these actions, the Sync_Param class initializes 
        instances of two different asyncio synchronizers -- an Event object and a Semaphore object.
        As new controller are instantiated externally, they are added to a list of controllers to
        be synchronously operated, and in.
      
        Member function "set_param(param,value)" uses the "asyncio.gather()" function to synchronously
        run the "LS4Controller.sync_set_param(index,param_value)" for all the controllers.

       
    """

    def __init__(
        self,
    ):
     
        # list of instances of LS4Controller, one for each synchronized controller
        self.controller_list=[]

        # total number of synced controllers
        self.num_controllers = 0
        
        #index within controller_list of the lead controller
        self.lead_index = None

        #self.sync_event = asyncio.Event()
        #self.sync_event.clear()

        # list of asyncio Semaphores, one for each controller
        self.sync_sem_list = []


    def add_controller(
        self,
        controller: LS4Controller = None, 
        lead_flag: bool = False
    ):

        """ add a controller to the list of synchronized controllers.
            Also set the sync_event, sync_sem, and leader attributes of the
            controller.
        """

        assert controller is not None, "controller is not instantiated"       
        if lead_flag:
           assert self.lead_index is None, "controller %d already assigned lead" % self.lead_index
           self.lead_index = self.num_controllers

        self.sync_sem_list.append(asyncio.Semaphore(0))
        self.controller_list.append(controller)

        controller.set_lead(lead_flag)
        controller.set_sync_index(self.num_controllers)
        self.num_controllers += 1


    def set_sync(self,sync_flag = False):
        for controller in self.controller_list:
            controller.set_sync(sync_flag)
            controller.set_sync_sem_list(self.sync_sem_list)
            controller.set_num_controllers(self.num_controllers)

    async def set_param(
        self,
        param: str = None, 
        value: int = None, 
        force: bool = False,
    ):

        """ set a parameter synchronously among controller cabled together to allow
            synchronous operation.
            
        """

        await self.controller_list[self.lead_index].acquire_semaphores()
        await asyncio.gather(*(self.controller_list[index].sync_set_param(param=param,\
                            value=value) for index in range(0,self.num_controllers)))


