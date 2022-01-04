# CBPi4 PID for I2C Analog Output KettleLogic
It is based on this cbpi3 Plugin (https://github.com/cgspeck/cbpi-pidsmartboil-withpump)

## Mash & Boil in single Kettle (e.g. Horter und Kalb)
- The Kettle logic is intended to be used in a single Kettle. It is a PID logic. 
- It runs on PID control until it reaches a specified temperature. Above that temperature it heates w/o PID logic until a specified boil temp is reached.
- Power to run boil can be specified in the plugin


### Installation:

You can install (or clone) it from the GIT Repo. In case of updates, you will find them here first:
- sudo pip3 install https://github.com/avollkopf/cbpi4-BM_PID_SmartBoilWithPump/archive/main.zip

Afterwards you will need to activate the plugin:
- cbpi add cbpi4-BM_PID_SmartBoilWithPump
	
- cbpi >= 4.0.0.45 from my fork is required. The setup will check, if this repo is installed

## Parameters:

![Settings](https://github.com/avollkopf/cbpi4-BM_PID_SmartBoilWithPump/blob/main/cbpi4-BM_PID_SmartBoilWithPump-logic.png?raw=true)

- Configurable:
	- P: Proportional - Takes current value into account
	- I: Integral - Takes past values into account
	- D: Derivative - Takes future values into account
	- Max Output: Maximum Power (%) to be used for PID during Ramp up -> 100%


Changelog:

- 04.01.22: first Version
