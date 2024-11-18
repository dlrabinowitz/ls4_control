import sys
import asyncio
import time

def print_flush(str):
    print(str)
    sys.stdout.flush()

async def wait_task(event,semaphore,delay,label=""):

    label = label + "__"
    print_flush(label+"wait_task: waiting for event")
    await event.wait()
    print_flush(label+"wait_task: done waiting for event")

    assert not semaphore.locked(),label+"ERROR: semaphore is locked"
    await asyncio.sleep(delay)
    
    print_flush(label+"wait_task: acquiring semaphore")
    await semaphore.acquire()
    print_flush(label+"wait_task: semaphore acquired")
    await asyncio.sleep(1)
    #print_flush(label+"wait_task: releasing semaphore")
    #semaphore.release()
    #print_flush(label+"wait_task: semaphore released")
    
async def test_semaphore(event,semaphore):
    await asyncio.sleep(3)
    print_flush("test_semaphore: releasing semaphores")
    semaphore.release()
    semaphore.release()
    semaphore.release()
    print_flush("test_semaphore: semaphores released")
    print_flush("test_semaphore: setting event")
    event.set()
    print_flush("test_semaphore: done setting event")
    print_flush("test_semaphore: waiting for semphore to lock")
    iteration=0
    while not semaphore.locked() and iteration<10:
       await asyncio.sleep(1)
       iteration += 1
    print_flush("test_semaphore:  semphore is locked")


async def test():
  semaphore=asyncio.Semaphore(1)
  event = asyncio.Event()
  await semaphore.acquire()

  await asyncio.gather(wait_task(event,semaphore,3,"a"),wait_task(event,semaphore,3,"b"),wait_task(event,semaphore,3,"c"),test_semaphore(event,semaphore))
  #await asyncio.gather(wait_task(semaphore,3),test_semaphore(semaphore))


asyncio.run(test())

