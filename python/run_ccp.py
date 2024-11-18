# run_ccp.py
#
# This is the main loop for the Camera Control Program (CCP) for the LS4 Camera.
# All it does is instantiate the LS4_CCP class, initialize it, and run it.
#
# While running, commands can be sent to the camera by executing the following:
#
#   echo "command args" | netcat -N host 5000
#
# where command is the command name, args are the command arguments, and
# host the the name of the maching running run_ccp.py
#
# Use command = "help" with no args to print the list of commands, their arguments, \
# and function.
#
# Use command = "shutdown" to terminal program.
#
# Use "command = "restart" to restart and reinitialize the instance of LS4_CCP.
#
# Use "command = "reboot to reboot and then restart LS4_CCP.
#
# After each command is executed, a reply is echoed to the terminal beginning
# with "DONE" if the command is successful, and "ERROR" if not.
#
import asyncio
from archon.ls4.ls4_ccp import LS4_CCP

async def main_loop():

    abort = False # set to True if external abort triggered
    error_msg = None
    status = None
    logger=None
    ls4_ccp=None
    done=False

    print("instantiating ls4_ccp")
    try:
      ls4_ccp = LS4_CCP(parse_args=True)
      logger=ls4_ccp.logger
    except Exception as e:
      error_msg = "exception instantiating ls4_ccp: %s" % e
   
    print("initializing ls4_ccp")
    try:
      error_msg = await ls4_ccp.init(restart=False, reboot=False)
    except Exception as e:
      error_msg = "exception initializing ls4_ccp: %s" % e

    restart = False
    reboot = False
    print("running ls4_ccp")
    while not done and error_msg is None:
      done=True
      status=None
      try:
        status=await ls4_ccp.run(restart=restart,reboot=reboot)
        if status is None:
          error_msg = "ls4_ccp status is None"
        elif 'error' in status and status['error']:
          error_msg = "error  running ls4_ccp"
          
      except Exception as e:
        error_msg = "exception running ls4_ccp: %s" %e

      if restart or reboot:
          restart = False
          reboot = False
          done=False

      if status is None:
         error_msg = "ls4_ccp status is None"
      elif 'restart' in status and status['restart']:
         restart = True
         if 'reboot' in status and status['reboot']:
            reboot = True
         logger.info("restart requested with reboot = %s" % reboot)
         done = False
      elif 'reboot' in status and status['reboot']:
         restart = True
         reboot = True
         logger.info("restart requested with reboot = %s" % reboot)
         done = False
      elif 'shutdown' in status and status['shutdown']:
         logger.info("shutdown requested")

    if error_msg is not None:
      if logger is not None:
        logger.error(error_msg)
      else:
        print(error_msg)

    print("done")
              
asyncio.run(main_loop())
