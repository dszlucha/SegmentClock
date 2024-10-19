# Built in libraries
import board
import gc
import microcontroller
import os
import rtc
import socketpool
import sys
import time
import wifi

# External libraries
import adafruit_connection_manager
from adafruit_ht16k33 import segments
from adafruit_httpserver import Server, Request, Response
import adafruit_ntp
import adafruit_requests

def isDoNotDistrub():
    """is do not disturb"""
    now = time.time()
    tm = time.localtime(now)
    min = 730
    max = 2200
    if tm.tm_wday < 5:
        min = 630
    hour = tm.tm_hour * 100 + tm.tm_min
    if hour >= min and hour <= max:
        return False
    else:
        return True

def setBrightness():
    """set display brightness to highest during sunlight and lowest after sunset"""
    dt = time.time()
    if dt > sunrise and dt < sunset:
        display.brightness = 1.0
    else:
        display.brightness = 0.0

def getWeather():
    """Get weather data including timezone"""
    global conditions
    global last_weather
    global sunrise
    global sunset
    global temperature
    global timezone
    global weather_data
    url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&units={units}&appid={apikey}"

    display.bottom_left_dot = True

    try:      
        with requests.get(url) as response:
            weather_data = response.json()
    except:
        return False

    display.bottom_left_dot = False

    last_weather = time.time()

    conditions = weather_data['weather'][0]['main']
    if conditions == 'Thunderstorm':
        conditions = 'Thdr'
    elif conditions == 'Drizzle':
        conditions = 'Drzl'
    elif conditions == 'Atmosphere':
        conditions = 'Atms'
    elif conditions == 'Clear':
        conditions = 'Clr '
    elif conditions == 'Clouds':
        conditions = 'Clds'

    dt = weather_data['dt']
    sunrise = weather_data['sys']['sunrise']
    sunset = weather_data['sys']['sunset']
    temperature = weather_data['main']['temp']
    timezone = weather_data['timezone']

    if dt > sunrise and dt < sunset:
        display.brightness = 1.0
    else:
        display.brightness = 0.0

    return True

def GetNTPTime():
    """Set time from NTP"""
    global last_ntp
    try:
        ntp = adafruit_ntp.NTP(pool, server="pool.ntp.org", tz_offset=timezone/3600, cache_seconds=3600)
    except:
        return False
    
    rtc.RTC().datetime = ntp.datetime
    last_ntp = time.time()

    return True

def getFormattedTime(epoch):
    """Returns formatted time given an epoch"""
    tm = time.localtime(epoch)
    return f'{tm.tm_year}-{tm.tm_mon:02}-{tm.tm_mday:02} {tm.tm_hour:02}:{tm.tm_min:02}:{tm.tm_sec:02}'

def getUptime(uptime):
    """Compute uptime given number of seconds"""
    days = int(uptime / 86400)
    hours = int((uptime - (days * 86400)) / 3600)
    minutes = int((uptime - (days * 86400) - (hours * 3600)) / 60)
    seconds = int((uptime - (days * 86400) - (hours * 3600) - (minutes * 60)))
    return f'{days} days, {hours} hours, {minutes} minutes, {seconds} seconds'

def displayTime():
    """Display time"""
    hour = (time.localtime().tm_hour + 11) % 12 + 1
    minute = time.localtime().tm_min
    display.print("{:>2}".format(hour) + "{:02d}".format(minute))
    display.colons[0] = colon
    if time.localtime().tm_hour > 11:
        display.top_left_dot = True
    else:
        display.top_left_dot = False

def displayTemperature():
    """Display temperature"""
    display.print("{:4.0f}".format(temperature))
    display.colons[0] = False
    display.top_left_dot = False

def displayConditions():
    display.print(conditions[:4])
    display.colons[0] = False
    display.top_left_dot = False

# Setup
program_uptime = time.monotonic()

# Create the I2C interface.
# i2c = busio.I2C(board.SCL, board.SDA)
i2c = board.STEMMA_I2C()

# Create the LED segment class.
# This creates a 7 segment 4 character display:
display = segments.BigSeg7x4(i2c)

# get settings for openweathermap
location = os.getenv("LOCATION")
units = os.getenv("UNITS")
apikey = os.getenv("APIKEY")

print("Connecting to WiFi")
#  connect to your SSID
try:
    wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
except:
    display.print('WiFi')
    time.sleep(60)
    import supervisor
    supervisor.reload() 
print("Connected to WiFi")

#  prints IP address to REPL
print("My IP address is", wifi.radio.ipv4_address)

pool = socketpool.SocketPool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
requests = adafruit_requests.Session(pool, ssl_context)
server = Server(pool, "/static", debug=True)
server.start(str(wifi.radio.ipv4_address))

# get weather data including timezone
if getWeather() == False:
    display.print('Err')
    time.sleep(60)
    import supervisor
    supervisor.reload()
#setBrightness()

# set time
if GetNTPTime() == False:
    display.print('Time')
    time.sleep(60)
    import supervisor
    supervisor.reload()

# flag for "flipping" colon
colon = True

# elapsed time counters for display and weather
last_monotonic = time.monotonic()
current_display = 0
display_counter = 0
weather_counter = 0
ntp_counter = 0

@server.route("/")
def base(request: Request):
    info = """
<style>
table {
  border-collapse: collapse;
  width: 100%;
}

th, td {
  text-align: left;
  padding: 8px;
}

tr:nth-child(even) {
  background-color: #D6EEEE;
}
</style>"""
    info += f'<table><tr><td>System:</td><td>{sys.implementation._machine}</td></tr>'
    info += f'<tr><td>Version:</td><td>{sys.version}</td></tr>'
    info += f'<tr><td>Temperature:</td><td>{microcontroller.cpu.temperature} deg C</td></tr>'
    info += f'<tr><td>Frequency:</td><td>{microcontroller.cpu.frequency/1000000} MHz</td></tr>'
    info += f'<tr><td>Reset reason:</td><td>{microcontroller.cpu.reset_reason}</td></tr>'
    info += f'<tr><td>Hostname:</td><td>{wifi.radio.hostname}</td></tr>'
    info += f'<tr><td>Channel:</td><td>{wifi.radio.ap_info.channel}</td></tr>'
    info += f'<tr><td>Power:</td><td>{wifi.radio.tx_power} dBm</td></tr>'
    info += f'<tr><td>RSSI:</td><td>{wifi.radio.ap_info.rssi} dBm</td></tr>'
    info += f'<tr><td>Current time:</td><td>{getFormattedTime(time.time())}</td></tr>'
    info += f'<tr><td>Last NTP:</td><td>{getFormattedTime(last_ntp)}</td></tr>'
    info += f'<tr><td>Brightness:</td><td>{display.brightness}</td></tr>'
    info += f'<tr><td>Do not distrub:</td><td>{isDoNotDistrub()}</td></tr>'
    info += f'<tr><td>System uptime:</td><td>{getUptime(time.monotonic())}</td></tr>'
    info += f'<tr><td>Program uptime:</td><td>{getUptime(time.monotonic() - program_uptime)}</td></tr>'
    info += f'<tr><td>Heap alloc:</td><td>{round(gc.mem_alloc()/1024)} kb</td></tr>'
    info += f'<tr><td>Heap free:</td><td>{round(gc.mem_free()/1024)} kb</td></tr>'
    info += f'<tr><td>Location:</td><td>{location}</td></tr>'
    info += f'<tr><td>Last Open Weather:</td><td>{getFormattedTime(last_weather)}</td></tr>'
    info += f'<tr><td>Sunrise:</td><td>{getFormattedTime(sunrise+timezone)}</td></tr>'
    info += f'<tr><td>Sunset:</td><td>{getFormattedTime(sunset+timezone)}</td></tr>'
    info += '<tr><td>Open Weather data:</td><td>'
    info += str(weather_data)
    info += '</td></tr></table>'
    return Response(request, info, content_type='text/html')

# Loop
while True:
    # one second counter
    if time.monotonic() - last_monotonic >= 1:
        last_monotonic = time.monotonic()
        colon = not colon
        display_counter += 1
        weather_counter += 1
        ntp_counter += 1
    
    # update time every 24 hours
    if ntp_counter >= 86400:
        ntp_counter = 0
        GetNTPTime()

    # change display every 3 seconds
    if display_counter >= 3:
        display_counter = 0
        current_display += 1

    # get weather data and set brightness every 5 minutes
    if weather_counter >= 300:
        weather_counter = 0
        getWeather()
        #setBrightness()

    # reset display
    if current_display > 1:
        current_display = 0

    # display time, temperature and conditions
    if current_display == 0 or isDoNotDistrub(): # or display.brightness == 0.0:
        displayTime()
    elif current_display == 1:
        displayTemperature()
    # else:
    #     displayConditions()
    pool_result = server.poll()
