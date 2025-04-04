#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: David Rabinowitz (david.rabinowitz@yale.edu)
# @Date: 2023-12-18
# @Filename: ls4_device.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

import asyncio
from clu.device import Device
from archon.controller.ls4_logger import LS4_Logger
import time 
#from clu.protocol import open_connection

__all__ = ["LS4_Device"]

#from typing import TypeVar

#T = TypeVar("T", bound="LS4_Device")


class LS4_TCPStreamClient:
    """An object containing a writer and reader stream to a TCP server."""

    def __init__(self, name: str, host: str, port: int, local_addr: tuple = ('127.0.0.1',4242),
                 ls4_logger = None, connection_timeout = 30):

        self.connection_timeout = connection_timeout

        self.ls4_logger=ls4_logger
        if self.ls4_logger is None:
           self.ls4_logger = LS4_Logger(name=name)

        self.info = self.ls4_logger.info
        self.debug = self.ls4_logger.debug
        self.warn= self.ls4_logger.warn
        self.error= self.ls4_logger.error
        self.critical= self.ls4_logger.critical

        self.name = name
        self.host = host
        self.port = port
        self.local_addr=local_addr
        self.reader = None
        self.writer = None


    async def open_connection(self,test = False, timeout_sec = None):
        """
           Creates the connection.

           If test is True, return True or False if connection is possible
           within timeout period time_sec.

           Otherwise, raise an exception if no connection is possible within specified
           timeout period.


        """

        self.debug("name = %s" % self.name)
        self.debug("local_addr = %s,%s" % self.local_addr)
        self.debug("host = %s" % self.host)
        self.debug("port = %d" % self.port)

        timeout_error_msg = None
        if timeout_sec is None:
           timeout_sec = self.connection_timeout

        # if local_addr is None or the port is 0, do not bind the socket to the address/port

        # if local_addr is None or the port is 0, do not bind the socket to the address/port
        if self.local_addr is None or self.local_addr[1] == 0 or self.local_addr[1] == "0":
           self.debug("open connection without binding : local_addr/port : %s "% str(self.local_addr))
           done = False
           elapsed_time = 0.0
           t_start = time.time()
           n_attempts= 0
           self.debug("waiting until successful connection or elapsed time > %7.3f sec" % timeout_sec)
           while not done and elapsed_time < timeout_sec:
             n_attempts += 1
             self.debug("connection attempt %d" % n_attempts)
             try:
                self.reader, self.writer = await asyncio.open_connection(\
                            host=self.host, port=self.port)
                self.debug("connection attempt %d successful" % n_attempts)
                done = True
             except Exception as e:
                self.debug("attempt %d, exception: %s" % (n_attempts,e))
                await asyncio.sleep(1)
                elapsed_time = time.time() - t_start

           if not done:
                timeout_error_msg = "connection to host %s on port %d timed out after %7.3f sec" %\
                          (self.host,self.port,timeout_sec)

        # otherwise bind. Note: After closing, there is a system-dependent delay before the port becomes
        # available again for socket IO.
        else:
           self.debug("open connection with binding : local_addr/port : %s "% str(self.local_addr))
           done = False
           elapsed_time = 0.0
           t_start = time.time()
           n_attempts= 0
           self.debug("waiting until successful connection or elapsed time > %7.3f sec" % timeout_sec)
           while not done and elapsed_time < timeout_sec:
             n_attempts += 1
             self.debug("connection attempt %d" % n_attempts)
             try:
                self.reader, self.writer = await asyncio.open_connection(\
                            host=self.host, port=self.port,  local_addr=self.local_addr)
                self.debug("connection attempt %d successful" % n_attempts)
                done = True
             except Exception as e:
                self.debug("attempt %d, exception: %s" % (n_attempts,e))
                await asyncio.sleep(1)
                elapsed_time = time.time() - t_start

      
        if test:
           if timeout_error_msg is not None:
              self.warn(timeout_error_msg)
              return False
           else:
              return True
        else:
           assert timeout_error_msg is None, timeout_error_msg

    async def close(self):
        """Close the stream connection."""

        if self.writer:
            self.debug("closing writer connection")
            self.writer.close()
            await self.writer.wait_closed()
            self.debug("done closing writer connection")

        else:
            raise RuntimeError("writer connection cannot be closed because it is not open.")

class LS4_Device(Device):

    def __init__(
        self,
        name: str,
        host: str,
        local_addr: tuple = ('127.0.0.1',4242),
        port: int = 4242,
        config: dict | None = None,
        ls4_logger = None,
        connection_timeout: float = 30.0
    ):

        self.ls4_logger=ls4_logger
        if self.ls4_logger is None:
           self.ls4_logger = LS4_Logger(name=name)

        self.info = self.ls4_logger.info
        self.debug = self.ls4_logger.debug
        self.warn= self.ls4_logger.warn
        self.error= self.ls4_logger.error
        self.critical= self.ls4_logger.critical
        self.connection_timeout = connection_timeout

        super(LS4_Device,self).__init__(host=host,port=port)
        self.name=name
        self.local_addr=local_addr
        self.config=config


    async def test_connection(self,timeout_sec =None):
        """ test for a connection within specified timeout period (or default if timeout_sec = None)"""

        result = False


        if self.is_connected():
           self.info("already connected to {self.name}")
           result = True

        else:
           if timeout_sec is None:
              timeout_sec = self.connection_timeout
           try:
             result,client = await self.ls4_open_connection(test=True, timeout_sec = timeout_sec)
             if result is True: 
                await self.ls4_close_connection(client)
           except Exception as e:
             error_msg = "exception testing connection: %s" %e
             result = False


        return result

    async def start(self):

        if self.is_connected():
            raise RuntimeError("connection is already running.")

        self._client = await self.ls4_open_connection()
        self.listener = asyncio.create_task(self._listen())

        #return self

    async def stop(self):

        if not self.is_connected():
            raise RuntimeError("no connection to stop.")

        await self._client.close()


    async def ls4_open_connection(self, test = False, timeout_sec = None):
        """Returns a TCP stream connection with a writer and reader """

        client = LS4_TCPStreamClient(name=self.name,host=self.host, port=self.port, local_addr=self.local_addr)

        result = await client.open_connection(test = test, timeout_sec = timeout_sec)
        
        if test:
           return result,client

        return client


    async def ls4_close_connection(self,client):
        """close  connections to TCP stream"""

        """
        Parameters
        ----------
        client : `.LS4_TCPStreamClient`
            A container for the stream reader and writer.
        """

        if client:
          await client.close()


