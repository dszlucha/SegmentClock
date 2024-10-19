# SegmentClock
Big LED segment clock displays the current time and temperature on a large 1.2" 4 digit 7 segment display.

# Parts
* [Adafruit QT Py S3 with 2MB PSRAM WiFi Dev Board with STEMMA QT](https://www.adafruit.com/product/5700)
* [Adafruit 1.2" 4-Digit 7-Segment Display w/I2C Backpack - Red](https://www.adafruit.com/product/1270)

# Dependencies
```sh
circup install adafruit-circuitpython-ht16k33
circup install adafruit-circuitpython-ntp
circup install adafruit-circuitpython-requests
circup install adafruit_connection_manager
circup install adafruit_httpserver
```
# settings.toml
```
# To auto-connect to Wi-Fi
CIRCUITPY_WIFI_SSID="my WiFi SSID"
CIRCUITPY_WIFI_PASSWORD="my WiFi SSID password"

# To enable the web workflow. Change this too!
# Leave the User field blank in the browser.
CIRCUITPY_WEB_API_PASSWORD="passw0rd"

# For openweathermap
LOCATION="my location"
UNITS="imperial"
APIKEY="my API key"
```
