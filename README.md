Weather CHIP
============================

Python program that interfaces with the following sensors to create a homemade weather station that updates to Adafruit IO

Although this was created on a CHIP, this should have no issues running on a Raspberry Pi or Beaglebone Black

[BMP180](https://www.adafruit.com/products/1603)
[AM2315](https://www.adafruit.com/products/1293)
[ADS1015](https://www.adafruit.com/products/1083)
[Photocell](https://www.adafruit.com/products/161)
[Anemometer](https://www.adafruit.com/products/1733)

- In a terminal execute the following, enter password for sudo when prompted:
  
  ```
  sudo apt-get install build-essential python-pip python-dev python-smbus git
  git clone https://github.com/xtacocorex/weather-chip.git
  cd weather-chip
  ./install.sh
  ```

- After installing, you will need to configure the code to use your personal Adafruit IO data:

 ```
 sudo nano /etc/aio.cfg
 ```

- To run:

 ```
 wxchip.py &
 ```

