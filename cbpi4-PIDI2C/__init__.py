
# -*- coding: utf-8 -*-

import asyncio
from asyncio import tasks
import logging
from unittest.mock import MagicMock, patch
import random
from cbpi.api import *
import time


@parameters([Property.Number("P", True, 0),
             Property.Number("I", True, 0),
             Property.Number("D", True, 0),
             Property.Number("max. output %", True, 100)])

class PIDI2C(CBPiKettleLogic):

   def init(self, props):
       self.a_p = float(self.props.get("P", 0))
       self.b_i = float(self.props.get("I", 0))
       self.c_d = float(self.props.get("D", 0))
       self.d_max_out = float(self.props.get("max. output %", 0))
       pass

   async def autoOff(self):
      self.finished=True
   
   async def on_stop(self):
        if self.finished == False:
            self.cbpi.notify('PIDI2C', 'Process stopped Manually. Please run Autotune again.', NotificationType.ERROR)
        await self.actor_off(self.heater)
        self.running = False

   async def run(self):
        self.finished = False
        self._logger = logging.getLogger(type(self).__name__)
        
        self.cbpi.notify('PID AutoTune', 'AutoTune In Progress. Do not turn off Auto mode until AutoTuning is complete', NotificationType.INFO)
        
        sampleTime = 1
        wait_time = 1
        p = float(self.a_p)
        i = float(self.b_i)
        d = float(self.c_d)
        maxout = float(self.d_max_out)
        try:
           pid = PIDI2C(sampleTime, p, i, d, 0, maxout)
        except Exception as e:
            self.cbpi.notify('PIDI2C', 'AutoTune Error: {}'.format(str(e)),NotificationType.ERROR)
            pid.log(str(e))
            await self.autoOff()
                
        while self.is_running():
            heat_percent = pid.calc(self.get_temp(), self.get_target_temp())
            heating_time = sampleTime * heat_percent / 100
            wait_time = sampleTime - heating_time
            self.heater_on(int(heat_percent))
            self.actor_power(int(heat_percent))
            self.sleep(heating_time)
            self.sleep(wait_time)

# Based on Arduino PID Library
# See https://github.com/br3ttb/Arduino-PID-Library
class PIDI2C(object):

    def __init__(self, sampleTimeSec, kp, ki, kd, outputMin=float('-inf'),
                 outputMax=float('inf'), getTimeMs=None):
        if kp is None:
            raise ValueError('kp must be specified')
        if ki is None:
            raise ValueError('ki must be specified')
        if kd is None:
            raise ValueError('kd must be specified')
        if sampleTimeSec <= 0:
            raise ValueError('sampleTimeSec must be greater than 0')
        if outputMin >= outputMax:
            raise ValueError('outputMin must be less than outputMax')

        self._logger = logging.getLogger(type(self).__name__)
        self._Kp = kp
        self._Ki = ki * sampleTimeSec
        self._Kd = kd / sampleTimeSec
        self._sampleTime = sampleTimeSec * 1000
        self._outputMin = outputMin
        self._outputMax = outputMax
        self._iTerm = 0
        self._lastInput = 0
        self._lastOutput = 0
        self._lastCalc = 0

        if getTimeMs is None:
            self._getTimeMs = self._currentTimeMs
        else:
            self._getTimeMs = getTimeMs

    def calc(self, inputValue, setpoint):
        now = self._getTimeMs()

        if (now - self._lastCalc) < self._sampleTime:
            return self._lastOutput

        # Compute all the working error variables
        error = setpoint - inputValue
        dInput = inputValue - self._lastInput

        # In order to prevent windup, only integrate if the process is not saturated
        if self._lastOutput < self._outputMax and self._lastOutput > self._outputMin:
            self._iTerm += self._Ki * error
            self._iTerm = min(self._iTerm, self._outputMax)
            self._iTerm = max(self._iTerm, self._outputMin)

        p = self._Kp * error
        i = self._iTerm
        d = -(self._Kd * dInput)

        # Compute PID Output
        self._lastOutput = p + i + d
        self._lastOutput = min(self._lastOutput, self._outputMax)
        self._lastOutput = max(self._lastOutput, self._outputMin)

        # Log some debug info
        self._logger.debug('P: {0}'.format(p))
        self._logger.debug('I: {0}'.format(i))
        self._logger.debug('D: {0}'.format(d))
        self._logger.debug('output: {0}'.format(self._lastOutput))

        # Remember some variables for next time
        self._lastInput = inputValue
        self._lastCalc = now
        return self._lastOutput

    def _currentTimeMs(self):
        return time.time() * 1000
  


def setup(cbpi):


    '''
    This method is called by the server during startup 
    Here you need to register your plugins at the server
    
    :param cbpi: the cbpi core 
    :return: 
    '''
    cbpi.plugin.register("PIDI2C", PIDI2C)    
    pass

