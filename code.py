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
import asyncio

def is_do_not_distrub() -> bool:
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

async def get_open_weather():
    """Get weather data including timezone"""
    global last_weather
    global sunrise
    global sunset
    global temperature
    global timezone
    global weather_data
    url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&units={units}&appid={apikey}"

    while True:
        display.bottom_left_dot = True

        try:      
            with requests.get(url) as response:
                weather_data = response.json()
            display.bottom_left_dot = False
            last_weather = time.time()
        except:
            pass

        dt = weather_data['dt']
        sunrise = weather_data['sys']['sunrise']
        sunset = weather_data['sys']['sunset']
        temperature = weather_data['main']['temp']
        timezone = weather_data['timezone']

        if dt > sunrise and dt < sunset:
            display.brightness = 1.0
        else:
            display.brightness = 0.0
        await asyncio.sleep(300)

async def get_ntp_time():
    """Set time from NTP"""
    global last_ntp
    while True:
        try:
            ntp = adafruit_ntp.NTP(pool, server="pool.ntp.org", tz_offset=timezone/3600, cache_seconds=3600)
            rtc.RTC().datetime = ntp.datetime
            last_ntp = time.time()
        except:
            pass
        await asyncio.sleep(86400)

def get_formatted_time(epoch: float) -> str:
    """Returns formatted time given an epoch"""
    tm = time.localtime(epoch)
    return f'{tm.tm_year}-{tm.tm_mon:02}-{tm.tm_mday:02} {tm.tm_hour:02}:{tm.tm_min:02}:{tm.tm_sec:02}'

def get_uptime(uptime: float) -> str:
    """Compute uptime given number of seconds"""
    days = int(uptime / 86400)
    hours = int((uptime - (days * 86400)) / 3600)
    minutes = int((uptime - (days * 86400) - (hours * 3600)) / 60)
    seconds = int((uptime - (days * 86400) - (hours * 3600) - (minutes * 60)))
    return f'{days} days, {hours} hours, {minutes} minutes, {seconds} seconds'

def display_time(show_colon: bool=True):
    """Display time"""
    hour = (time.localtime().tm_hour + 11) % 12 + 1
    minute = time.localtime().tm_min
    display.print("{:>2}".format(hour) + "{:02d}".format(minute))
    display.colons[0] = show_colon
    if time.localtime().tm_hour > 11:
        display.top_left_dot = True
    else:
        display.top_left_dot = False

async def update_display():
    """Cycle through time, and temperature"""
    while True:
        # display time

        display_time()
        await asyncio.sleep(1)
        
        display_time(False)
        await asyncio.sleep(1)

        if not is_do_not_distrub():
            display_time()
            await asyncio.sleep(1)

            # display temperature
            display.print("{:4.0f}".format(temperature))
            display.colons[0] = False
            display.top_left_dot = False
            await asyncio.sleep(3)

async def handle_http_requests():
    """Run the web server"""
    while True:
        # Process any waiting requests
        server.poll()
        await asyncio.sleep(0)

async def main():
    """Main entry point"""

    weather_task = asyncio.create_task(get_open_weather())
    ntp_task = asyncio.create_task(get_ntp_time())
    display_task = asyncio.create_task(update_display())
    http_task = asyncio.create_task(handle_http_requests())
    await asyncio.gather(weather_task, ntp_task, display_task, http_task)

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

pool = socketpool.SocketPool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
requests = adafruit_requests.Session(pool, ssl_context)
server = Server(pool, debug=True)

@server.route("/")
def base(request: Request) -> Response:
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
    info += f'<tr><td>Frequency:</td><td>{microcontroller.cpu.frequency/1000000} MHz</td></tr>'
    info += f'<tr><td>Reset reason:</td><td>{microcontroller.cpu.reset_reason}</td></tr>'
    info += f'<tr><td>Hostname:</td><td>{wifi.radio.hostname}</td></tr>'
    info += f'<tr><td>Channel:</td><td>{wifi.radio.ap_info.channel}</td></tr>'
    info += f'<tr><td>Power:</td><td>{wifi.radio.tx_power} dBm</td></tr>'
    info += f'<tr><td>RSSI:</td><td>{wifi.radio.ap_info.rssi} dBm</td></tr>'
    info += f'<tr><td>Current time:</td><td>{get_formatted_time(time.time())}</td></tr>'
    info += f'<tr><td>Last NTP:</td><td>{get_formatted_time(last_ntp)}</td></tr>'
    info += f'<tr><td>Brightness:</td><td>{display.brightness}</td></tr>'
    info += f'<tr><td>Do not distrub:</td><td>{is_do_not_distrub()}</td></tr>'
    info += f'<tr><td>System uptime:</td><td>{get_uptime(time.monotonic())}</td></tr>'
    info += f'<tr><td>Program uptime:</td><td>{get_uptime(time.monotonic() - program_uptime)}</td></tr>'
    info += f'<tr><td>Heap alloc:</td><td>{round(gc.mem_alloc()/1024)} kb</td></tr>'
    info += f'<tr><td>Heap free:</td><td>{round(gc.mem_free()/1024)} kb</td></tr>'
    info += f'<tr><td>Location:</td><td>{location}</td></tr>'
    info += f'<tr><td>Last Open Weather:</td><td>{get_formatted_time(last_weather)}</td></tr>'
    info += f'<tr><td>Sunrise:</td><td>{get_formatted_time(sunrise+timezone)}</td></tr>'
    info += f'<tr><td>Sunset:</td><td>{get_formatted_time(sunset+timezone)}</td></tr>'
    info += '<tr><td>Open Weather data:</td><td>'
    info += str(weather_data)
    info += '</td></tr></table>'
    return Response(request, info, content_type='text/html')

server.start(str(wifi.radio.ipv4_address))
    
asyncio.run(main())
