/*
 * Title:        PRisme Control Center
 * Description:  This program is intented to work with the Python
                 application of the same name to control the
                 robot from a computer.
 * Author:       Karl Kangur <karl.kangur@gmail.com>
 * Version:      1.0
 */
#include <robopoly.h>
#include <LinearCamera.h>

unsigned char i, j;
char serialValue;
unsigned int intTime;
char leftSpeed, rightSpeed;
unsigned char irSensors[5];

unsigned char infraRedAnalogRead()
{
  // turn IR emitters on
  digital_write(PORTC, 0, 1);
  for(j = 0; j < 5; j++)
  {
    // select channel
    ADMUX = (ADMUX & 0xf0) + j;
    // start conversion
    ADCSRA |= (1 << ADSC);
    // wait for the conversion to finish
    while(ADCSRA & (1 << ADSC));
    // save temporary value
    irSensors[j] = ADCH;
  }
  // turn IR emitters off
  digital_write(PORTC, 0, 0);
}

int main()
{
  pin_mode(PORTC, 2, 1);
  serialSetup();
  lcam_setup();
  unsigned char *lcam_dataPtr = lcam_getdata();

  intTime = 100;
  
  // emitter pin
  pin_mode(PORTC, 0, 1);
  // enable ADC and set prescaler to 128 (lower it to make it faster)
  ADCSRA = (1 << ADEN) | (1 << ADPS2) | (1 << ADPS1) | (1 << ADPS0);
  // left adjust result, return 8-bit value
  ADMUX = (1 << ADLAR);

  while(1)
  {
    if(serialAvailable())
    {
      switch(serialRead())
      {
      case 'd':
        // send linear camera data
        lcam_integrate(intTime);
        lcam_read();
        for(i = 0; i < 102; i++)
        {
          serialRaw(*(lcam_dataPtr + i));
        }
        // send IR sensor values
        infraRedAnalogRead();
        for(i = 0; i < 5; i++)
        {
          serialRaw(irSensors[4 - i]);
        }
        break;
      case 't':
        while(!serialAvailable());
        intTime = ((unsigned char)serialRead() << 8);
        while(!serialAvailable());
        intTime += (unsigned char)serialRead();
        lcam_reset();
        break;
      case 'c':
        serialRaw(intTime >> 8);
        serialRaw(intTime & 0xff);
        break;
      case 's':
        while(!serialAvailable());
        leftSpeed = serialRead();
        while(!serialAvailable());
        rightSpeed = serialRead();
        setSpeed(leftSpeed, rightSpeed);
        break;
      case 'r':
        setSpeed(0, 0);
        break;
      }
    }
  }
  return 0;
}

