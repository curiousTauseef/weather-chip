#!/bin/bash

# GET LIBRARIES
# ADS1x15
git clone https://github.com/adafruit/Adafruit_Python_ADS1x15.git
cd Adafruit_Python_ADS1x15
sudo python setup.py install
cd ..

# BMP180
git clone https://github.com/adafruit/Adafruit_Python_BMP.git
cd Adafruit_Python_BMP
sudo python setup.py install
cd ..

# Adafruit_GPIO (my fork)
git clone https://github.com/xtacocorex/Adafruit_Python_GPIO.git
cd Adafruit_Python_GPIO
sudo python setup.py install
cd ..

# Adafruit IO
git clone https://github.com/adafruit/io-client-python.git
cd io-client-python
sudo python setup.py install
cd ..

# AM2315.py
git clone https://github.com/xtacocorex/Simple_AM2315.git
cd Simple_AM2315
sudo python setup.py install
cd ..

# COPY wxchip.py TO /usr/bin
echo "Installing wxchip.py"
sudo cp ./wxchip.py /usr/bin/wxchip.py

# COPY aio.cfg TO /etc
echo "Installing aio.cfg"
sudo cp ./aio.cfg /etc/aio.cfg

