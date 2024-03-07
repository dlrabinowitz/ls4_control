import asyncio
from archon import log

# utility functions for working with asyncio Events

async def wait_events(
    event_list: list[asyncio.Event]=[],
    sync_index: int = -1,
):
    """ wait for  for all (sync_index-1) or a particular (sync_index>-1) 
        event in event_list to be set
    """

    assert sync_index in range(-1,len(event_list)),\
            "sync_index [%d] out of range [-1 to %d]" % (sync_index,len(event_list))

    if sync_index > -1:
       log.debug("wating for event for sync index %d" % sync_index)
       result = await event_action(event_list[sync_index],"wait")
       return [result]
    else:
       result = await asyncio.gather(*(event_action(event,"wait") for event in event_list))
       log.debug("wait_events: result = %s" % result)
       return result



async def defunct_wait_events(
    event_list: list[asyncio.Event]=[],
    set_flag: bool = True,
    sync_index: int = -1,
    timeout_msec: float = 1000.0
):
    """ wait up to timeout_msec for all (sync_index-1) 
        or a particular (sync_index>-1) event in event_list to have 
        specified setting (set_flag = True/False)
    """

    assert sync_index in range(-1,len(event_list)),\
            "sync_index [%d] out of range [-1 to %d]" % (sync_index,len(event_list))

    wait_interval = 0.01 # sec
    t_start = time.time()
    dt = 0.0
    done = False
    timeout = False
    while not done and not timeout:
        dt = (time.time() - t_start)*1000.0
        if await check_events(event_list=event_list,sync_index=sync_index,set_flag=set_flag):
           done=True
        elif dt > timeout_msec:
           timeout=True
        else:
           asyncio.sleep(wait_interval)

    if timeout:
       print("timeout waiting for sync_events to clear")

    return done

async def check_events(
    event_list: list[asyncio.Event]=[],
    sync_index: int = -1,
    set_flag: bool = True
):

    """ check that all (sync_index==1) or a specific event  (sync_index>-1) in event_list 
        have status matching set_flag 
    """
    assert sync_index in range(-1,len(event_list)),\
            "sync_index [%d] out of range [-1 to %d]" % (sync_index,len(event_list))

    index = 0
    all_correct = True
    
    if sync_index > -1:
       log.debug("checking event for sync index %d" % sync_index)
       if event_list[sync_index].is_set() != set_flag:
         all_correct = False
    else:
       result = await asyncio.gather(*(event_action(event,"is_set") for event in event_list))
       """
       result = []
       index = 0
       for event in event_list:
          r = event.is_set()
          log.debug("event %d state: %s" % (index,r))
          result.append(r)
       """
       if (not set_flag)  in result:
          log.debug ("check_events unwanted result (all should be %s) : %s" % (set_flag,result))
          all_correct = False

    return all_correct

async def set_events(
    event_list: list[asyncio.Event]=[],
    sync_index: int = -1 
):

    """ set  all (sync_index==1) or a specific event  (sync_index>-1) in event_list """

    assert sync_index in range(-1,len(event_list)),\
            "sync_index [%d] out of range [-1 to %d]" % (sync_index,len(event_list))

    if sync_index > -1:
       log.debug("setting event for sync index %d" % sync_index)
       result = await event_action(event_list[sync_index],"set")
       results = [result]
    else:
       result = await asyncio.gather(*(event_action(event,"set") for event in event_list))
       return result


async def clear_events(
    event_list: list[asyncio.Event]=[],
    sync_index: int = -1 
):
    """ clear all (sync_index==1) or a specific event  (sync_index>-1) in event_list """
    

    assert sync_index in range(-1,len(event_list)),\
            "sync_index [%d] out of range [-1 to %d]" % (sync_index,len(event_list))

    if sync_index > -1:
       log.debug("clearing event for sync index %d" % sync_index)
       result = event_list[sync_index].clear()
       return [result]

    else:
       result = await asyncio.gather(*(event_action(event,"clear") for event in event_list))
       """
       result=[]
       index = 0
       for event in event_list:
           log.debug("clearing event %d" % index)
           result.append(event.clear())
           log.debug("result of clearing: %s" % event.is_set())
       """
       log.debug("clear_events result: %s" % result)

       return result

async def event_action(
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


