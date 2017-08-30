#!/usr/bin/python

# MODULE IMPORTS
import Adafruit_BMP.BMP085 as BMP085  # ODDITY, HAVE TO DO IT THIS WAY
import Adafruit_ADS1x15
import Adafruit_IO
from am2315 import AM2315
import ConfigParser
import time
import signal
import sys
import math
import subprocess
import threading
import logging
import os

# GLOBAL VARIABLES

#  - 2/3 = +/-6.144V
#  -   2 = +/-2.048V
ADCGAIN6VDC = 2/3
ADCGAIN6VDCVOLTS = 6.144
ADCGAIN2VDC = 2
ADCGAIN2VDCVOLTS = 2.048
ADCRESOLUTION = 2048

# ADC CHANNEL SENSORS
PHOTOCELL = 0
ANEMOMETER = 1

# ATMOSPHERICS
CTOK = 273.15
R_AIR = 287.058
P_FLAT_MAX_DELTA = 20.0
P_FLAT_MIN_DELTA = -20.0

LEDOFFTIMER = 5
SLEEPTIME = 120
DATASENDSLEEP = 0.01

# CONNECT/DISCONNECT EVENTS
connected = threading.Event()
disconnected = threading.Event()

# CLASSES
class WeatherStation:
    def __init__(self, io_client_conf="/etc/wxchip.cfg", io_client_type="mqtt"):
        # VARIABLES
        self.io_client = None
        self.io_client_conf = io_client_conf
        self.io_client_type = io_client_type
        self.io_key = None
        self.io_user = None
        self.data = [
            ["wxchip-BMP180-temp", -1],
            ["wxchip-BMP180-baro", -1],
            ["wxchip-BMP180-alt", -1],
            ["wxchip-BMP180-density", -1],
            ["wxchip-lux", -1],
            ["wxchip-windspeed", -1],
            ["wxchip-AM2315-temp", -1],
            ["wxchip-AM2315-humidity", -1]]
        self.dead = False
        self.last_pres_avg = 0
        self.pres_trending = "flat"
    
        # READ OUR CONFIG
        config = ConfigParser.ConfigParser()
        config.read(self.io_client_conf)
        self.io_key = config.get("aio", "key", None)
        self.io_user = config.get("aio", "username", None)
        # GET THE BUS NUMBERS FOR THE DEVICES
        self.bmp180_bus = config.get("devices", "bmp180_bus", 1)
        self.ads1015_bus = config.get("devices", "ads1015_bus", 1)
        self.am2315_bus = config.get("devices", "am2315_bus", 1)
        
        if self.io_key == None:
            text = "No AIO Key found in %s" % self.io_client_conf
            raise ValueError(text)
        
        if self.io_user == None and self.io_client_type == "mqtt":
            text = "No AIO User found in %s" % self.io_client_conf
            raise ValueError(text)
        
        # CREATE OUR IO_CLIENT
        if self.io_client_type == "mqtt":
            self.io_client = Adafruit_IO.MQTTClient(self.io_user, self.io_key)
            logging.debug('Setting up AIO callbacks')
            self.io_client.on_connect    = io_connected
            self.io_client.on_disconnect = io_disconnected
        elif self.io_client_type == "rest":
            self.io_client = Adafruit_IO.Client(self.io_key)

        # CREATE OUR DEVICE OBJECTS
        logging.debug('Setting up objects')
        self.bmp180 = BMP085.BMP085(busnum=self.bmp180_bus)
        self.ads1015 = Adafruit_ADS1x15.ADS1015(busnum=self.ads1015_bus)
        #self.am2315 = AM2315.AM2315(busnum=self.am2315_bus)

    def calc_lux(self,volts):
        lux = 0.0
        # GENERIC CURVE FIT FROM https://learn.adafruit.com/photocells/using-a-photocell
        #lux = 0.1624 * math.exp(1.6482 * volts)
    
        # AXEL BENZ CURVE FIT FROM https://learn.adafruit.com/photocells/using-a-photocell
        lux = 1.833 * math.exp(1.8344 * volts)
    
        return lux
    
    def compute_density(self,pres,temp):
        return pres / (R_AIR * (temp + CTOK))
    
    def calc_windspeed(self,volts):
        return -1

    #def status_led_off(self):
    #    logging.debug('CHIP LED off')
    #    # CANNOT USE I2C LIB AS WE NEED TO FORCE THE COMMAND DUE TO THE KERNEL OWNING THE DEVICE
    #    subprocess.call('/usr/sbin/i2cset -f -y 0 0x34 0x93 0x0', shell=True)
    #
    #def status_led_on(self):
    #    logging.debug('CHIP LED on')
    #    # CANNOT USE I2C LIB AS WE NEED TO FORCE THE COMMAND DUE TO THE KERNEL OWNING THE DEVICE
    #    subprocess.call('/usr/sbin/i2cset -f -y 0 0x34 0x93 0x1', shell=True)

    def do_connect(self):
        logging.debug("In do_connect: type: %s",self.io_client_type)
        if self.io_client_type == "mqtt":
            self.io_client.connect()
            self.io_client.loop_background()
            
            while not connected.isSet():
                 continue
                 
            connected.clear()

    def kill(self):
        self.dead = True

    def run(self):
        self.do_connect()
    
        while not self.dead:
        
            try:
                if disconnected.isSet():
                    self.do_connect()
            
                logging.debug("Gathering data")
                # GET BMP805 DATA
                self.data[0][1] = self.bmp180.read_temperature() # C
                self.data[1][1] = self.bmp180.read_pressure()    # Pa
                self.data[2][1] = self.bmp180.read_altitude()    # m
                self.data[3][1] = self.compute_density(self.data[1][1],self.data[0][1]) # kg/m^3
    
                # GET ADC CHANNEL 0: PHOTOCELL
                photocell_volts = self.ads1015.read_adc(PHOTOCELL, gain=ADCGAIN6VDC) * (ADCGAIN6VDCVOLTS/ADCRESOLUTION)
                self.data[4][1] = self.calc_lux(float(photocell_volts))
    
                # GET ADC CHANNEL 1: ANEMOMETER
                anemometer_volts = self.ads1015.read_adc(ANEMOMETER, gain=ADCGAIN2VDC) * (ADCGAIN2VDCVOLTS/ADCRESOLUTION)
                self.data[5][1] = self.calc_windspeed(float(anemometer_volts))
    
                # GET AM2315 DATA
                #self.data[7][1], self.data[6][1] = self.am2315.read_humidity_temperature()
    
                # TURN OFF THE LED
                #self.status_led_off()
                
                # PUBLISH DATA
                try:
                    logging.debug("Sending data: client type: %s", self.io_client_type)
                    for data in self.data:
                        tmp = "%.3f" % data[1]
                        if self.io_client_type == "mqtt":
                            self.io_client.publish(data[0], tmp)
                        else:
                            self.io_client.send(data[0], tmp)
                        time.sleep(DATASENDSLEEP)
                    logging.debug("Sending data complete")
                                        
                except Exception, e:
                    logging.exception('** something broke in publish **')
                    raise
                    
                #self.status_led_on()
                logging.debug("Starting sleep: %d seconds",SLEEPTIME)
                time.sleep(SLEEPTIME)
        
            except Exception, e:
                logging.exception('** something else broke **')

# FUNCTIONS
def signal_handler(signal, frame):
        logging.critical('killing wx-chip program!')
        sys.exit(1)
signal.signal(signal.SIGINT, signal_handler)

def io_connected(client):
    logging.info('Connected to wx-chip data repo on io.adafruit.com')
    ISCONNECTED = True
    connected.set()
    disconnected.clear()

def io_disconnected(client):
    logging.info('Disconnected from wx-chip data repo')
    connected.clear()
    disconnected.set()
    #sys.exit(1)

def Main():

    # WRITE PID TO FILE
    pid = os.getpid()
    f = open("/tmp/wx-chip.pid","w")
    f.write(str(pid))
    f.close()

    # SETUP LOGGING
    logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s\t%(levelname)s\t%(message)s',
                    datefmt='%m-%d %H:%M',
                    filename='/tmp/wx-chip-debug.log',
                    filemode='w')
    #formatter = logging.Formatter('%(asctime)s\t%(levelname)s\t%(message)s')
    #ch = logging.StreamHandler()
    #ch.setLevel(logging.DEBUG)
    #ch.setFormatter(formatter)
    #logging.getLogger('').addHandler(ch)

    # SETTING UP WEATHER STATION
    logging.debug("Creating weather station")
    connected.clear()
    disconnected.clear()
    wxstation = WeatherStation(io_client_type="mqtt")    

    # RUN THE WEATHER STATION
    wxstation.run()
    
if __name__ == "__main__":
    Main()
