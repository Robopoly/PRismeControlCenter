# PRisme Control Center

![PRisme Control Center screenshot](https://raw.github.com/Robopoly/PRismeControlCenter/master/images/screenshot.png)

The PRisme Control Center allows to get serial data from the PRisme and send instructions to it. It's main purpose is to show how to program a cross-platform application with a user interface with Python for the PRisme.

## Usage
The PRisme has to be loaded with the corresponding program for it (which is in _/PRismeControlCenter_ folder) in order for this application to work. It is made to be robust and solve problems constructively by identifiying the problem when possible (such as connectivity issues).

The application should never crash when something unpredictable happens (such as disconnection), but when disconnecting the device (USB) while the serial connection is live it may crash the computer.

The application has the following dependencies: `wx, string, time, serial, threading, subprocess` - some might already be installed on some systems.

One can modify the linear camera intergration time in microseconds if necessary, the minimum value being 0 and maximum is 65535. By default 100 works quite well for an incandescent bulb, a LED source may need a longer integration time.

The wheel speed can be set from 0 to 100%. One can use the arrow keys to control the wheels, space-bar to stop.

## Connectivity
The program will read the first 5 analog port values where IR sensors should be connected, so on `PORTA0-5`. In the application when an obstacle is detected the field background will, proportionnaly to the value, turn red. When using an incandescent bulb for the light source it will emit lots of IR and the IR sensors will saturate.

The linear camera connectivity is found it the [respective documentation](http://robopoly.epfl.ch/prisme/documentation-en).
