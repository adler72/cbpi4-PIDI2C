import asyncio
import logging
from cbpi.api import *
import time


@parameters([Property.Actor(label = "Heater_Relais",description="Relais for Heater on"),
             Property.Number(label="P", configurable=True, default_value=117.0795, description="P Value of PID"),
             Property.Number(label="I", configurable=True, default_value=0.2747, description="I Value of PID"),
             Property.Number(label="D", configurable=True, default_value=41.58, description="D Value of PID"),
             Property.Select(label="SampleTime", options=[2,5], description="PID Sample time in seconds. Default: 5 (How often is the output calculation done)"),
             Property.Number(label="Max_Boil_Output", configurable=True, default_value=85,
                             description="Power when Max Boil Temperature is reached."),
             Property.Number(label="Max_Boil_Temp", configurable=True, default_value=98,
                             description="When Temperature reaches this, power will be reduced to Max Boil Output."),
             Property.Number(label="Max_PID_Temp", configurable=True,
                             description="When this temperature is reached, PID will be turned off")])
class PIDI2C(CBPiKettleLogic):

    def __init__(self, cbpi, id, props):
        super().__init__(cbpi, id, props)
        self._logger = logging.getLogger(type(self).__name__)
        self.sample_time, self.max_output, self.pid = None, None, None
        self.work_time, self.rest_time, self.max_output_boil = None, None, None
        self.max_boil_temp, self.max_pid_temp, self.max_pump_temp = None, None, None
        self.kettle, self.heater, self.agitator, self.actor = None, None, None, None
        self.actors = []
        if self.props.get("Heater_Relais", None) is not None:
            self.actors.append(self.props.get("Heater_Relais"))
            
    async def on_stop(self):
        # ensure to switch also pump off when logic stops
        await self.actor_off(self.agitator)
        await self.actor_off(self.actor)
        
   
    # subroutine that controlls temperature via pid controll
    async def temp_control(self):
        await self.actor_on(self.heater,0)
        logging.info("Heater on with zero Power")
        heat_percent_old = 0
        while self.running:
            current_kettle_power= self.heater_actor.power
            # get current temeprature
            sensor_value = current_temp = self.get_sensor_value(self.kettle.sensor).get("value")
            # get the current target temperature for the kettle
            target_temp = self.get_kettle_target_temp(self.id)
            # if current temperature is higher the defined boil temp, use fixed heating percent instead of PID values for controlled boiling
            if current_temp >= self.max_boil_temp:
                heat_percent = self.max_output_boil
            # if current temperature is above max pid temp (should be higher than mashout temp and lower then max boil temp) 100% output will be used untile boil temp is reached
            elif current_temp >= self.max_pid_temp:
                heat_percent = self.max_output
            # at lower temepratures, PID algorythm will valculate heat percent value
            else:
                heat_percent = self.pid.calc(sensor_value, target_temp)

            # Test with actor power
            if (heat_percent != heat_percent_old) or (heat_percent != current_kettle_power):
                await self.actor_on(self.actor)
                await self.actor_set_power(self.heater,heat_percent)
                heat_percent_old = heat_percent
            await asyncio.sleep(self.sample_time)

    async def run(self):
        try:
            self.sample_time = int(self.props.get("SampleTime",5))
            self.max_output = 100
            p = float(self.props.get("P", 12.0))
            i = float(self.props.get("I", 0.05))
            d = float(self.props.get("D", 0))
            self.pid = PIDArduino(self.sample_time, p, i, d, 0, self.max_output)

            self.work_time = float(self.props.get("Rest_Interval", 600))
            self.rest_time = float(self.props.get("Rest_Time", 60))
            self.max_output_boil = float(self.props.get("Max_Boil_Output", 85))
            
            self.TEMP_UNIT = self.get_config_value("TEMP_UNIT", "C")
            boilthreshold = 98 if self.TEMP_UNIT == "C" else 208
            maxpidtemp = 88 if self.TEMP_UNIT == "C" else 190
            maxpumptemp = 88 if self.TEMP_UNIT == "C" else 190


            self.max_boil_temp = float(self.props.get("Max_Boil_Temp", boilthreshold))
            self.max_pid_temp = float(self.props.get("Max_PID_Temp", maxpidtemp))
            
            self.kettle = self.get_kettle(self.id)
            self.heater = self.kettle.heater
            self.agitator = self.kettle.agitator
            self.actor = self.props.get("Heater_Relais", None)
            self.heater_actor = self.cbpi.actor.find_by_id(self.heater)
                     
            logging.info("CustomLogic P:{} I:{} D:{} {} {}".format(p, i, d, self.kettle, self.heater))

            temp_controller = asyncio.create_task(self.temp_control())

            await temp_controller

        except asyncio.CancelledError as e:
            pass
        except Exception as e:
            logging.error("PIDI2C Error {}".format(e))
        finally:
            self.running = False
            await self.actor_off(self.heater)
            for actor in self.actors:
                await self.cbpi.actor.off(actor)
            
          
# Based on Arduino PID Library
# See https://github.com/br3ttb/Arduino-PID-Library
class PIDArduino(object):

    def __init__(self, sampleTimeSec, kp, ki, kd, outputMin=float('-inf'),
                 outputMax=float('inf'), getTimeMs=None):
        if kp is None:
            raise ValueError('kp must be specified')
        if ki is None:
            raise ValueError('ki must be specified')
        if kd is None:
            raise ValueError('kd must be specified')
        if float(sampleTimeSec) <= float(0):
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
        if self._outputMax > self._lastOutput > self._outputMin:
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

   
