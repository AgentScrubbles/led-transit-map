
from transit import Route, Vehicle, Stop, Trip
from strip_config import LightStop, StripConfig, LightStatus, BoundingArea
import os
import sys
import time
import argparse
import json
from shapely.geometry import Polygon, Point, LinearRing

# Parse command line arguments early
parser = argparse.ArgumentParser(description='LED Transit Map')
parser.add_argument('--debug', action='store_true',
                    help='Run in debug mode with terminal visualization (no hardware required)')
args = parser.parse_args()

DEBUG_MODE = args.debug or os.getenv('LED_DEBUG', '').lower() in ('1', 'true', 'yes')

if DEBUG_MODE:
    print("Running in DEBUG MODE - using terminal visualizer")
    from led_visualizer import create_fake_strip, render as render_leds
    NEOPIXEL_AVAILABLE = False

    class _FakeBoard:
        D18 = "D18"
        D10 = "D10"
        D21 = "D21"

    import board
    board = _FakeBoard()
else:
    try:
        import board
        import neopixel
        NEOPIXEL_AVAILABLE = True
    except Exception:
        NEOPIXEL_AVAILABLE = False
        # Simple shim so code referring to board.D18 still works
        class _FakeBoard:
            D18 = None
            D10 = None
            D21 = None

        board = _FakeBoard()

from onebusaway import OnebusawaySDK
from dotenv import main

from colorama import init as colorama_init
from colorama import Fore
from colorama import Style


def api_call_with_retry(api_func, *args, max_retries=3, retry_delay=2, **kwargs):
    """
    Wrapper for API calls that retries on failure.
    Returns None if all retries fail.
    """
    for attempt in range(max_retries):
        try:
            result = api_func(*args, **kwargs)
            if result is not None:
                return result
            print(f"{Fore.YELLOW}API returned None, attempt {attempt + 1}/{max_retries}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}API call failed (attempt {attempt + 1}/{max_retries}): {e}{Style.RESET_ALL}")

        if attempt < max_retries - 1:
            time.sleep(retry_delay * (attempt + 1))  # Exponential backoff

    return None


# PACKAGE SETUP
main.load_dotenv()
client = OnebusawaySDK(
    api_key=os.getenv("ONEBUSAWAY_API_KEY")
)
colorama_init()


# CONSTANT VARIABLES

realtime_url = os.getenv('realtime_url')
agency = int(os.getenv('AGENCY_ID'))
last_set_colors = {}
stop_radius = 0.01
loop_sleep = 4
light_set_delay = 0.01

light_colors = {
    LightStatus.EMPTY: 0x000000,
    LightStatus.STATION: 0x7F1200,
    LightStatus.OCCUPIED: 0x3DAE2B,
    LightStatus.DISABLED_STATION: 0xFF0000
}


# ON START LIGHTSTRIP CONFIG

with open('strips.json') as json_data:
    led_config = json.load(json_data)

def make_strip(pin, length, brightness=0.1):
    if DEBUG_MODE:
        return create_fake_strip(pin, length, brightness=brightness)
    elif NEOPIXEL_AVAILABLE:
        return neopixel.NeoPixel(pin, length, brightness=brightness)
    else:
        return None

strips = {
    1: {
        'neopixel': make_strip(board.D18, 320),
        'length': 320
    },
    2: {
        'neopixel': make_strip(board.D10, 68),
        'length': 68
    },
    3: {
        'neopixel': make_strip(board.D21, 68),
        'length': 68
    }
}

# HELPER METHODS

def cls():
    os.system('cls' if os.name=='nt' else 'clear')


# LIGHTSTRIP METHODS

def clear_lights():
    color = light_colors.get(LightStatus.EMPTY)
    for strip_idx in strips:
        strip_config = strips.get(strip_idx)
        strip = strip_config.get('neopixel')
        if (strip is not None):
            strip.fill(color)

def clear_single_led(led_code: str):
    set_single_led(led_code, 0x000000)

def gamma_correction(value):
    gamma = 2.5  # Example gamma value; adjust as needed
    corrected_value = int((value / 255.0) ** (1.0 / gamma) * 255)
    return min(max(corrected_value, 0), 255)

def hex_to_rgb(hex_color):
    # Extract the red, green, and blue components from the hex color
    r = (hex_color >> 16) & 0xFF  # Extract the first 8 bits (red)
    g = (hex_color >> 8) & 0xFF   # Extract the next 8 bits (green)
    b = hex_color & 0xFF          # Extract the last 8 bits (blue)
    
    r = gamma_correction(r)
    g = gamma_correction(g)
    b = gamma_correction(b)
    return (r, g, b)

def print_colored(text, hex_color):
    # Convert hex color to RGB
    r, g, b = hex_to_rgb(hex_color)
    
    # Construct ANSI escape code for RGB
    rgb_color_code = f'\033[38;2;{r};{g};{b}m'
    
    # Print the text with the color
    print(f'{rgb_color_code}{text}{Style.RESET_ALL}')

def set_single_led(led_code: str, status_or_color):

    if isinstance(status_or_color, LightStatus):
        color = light_colors.get(status_or_color)
    else:
        color = status_or_color
    color = hex_to_rgb(color)
    arr = led_code.split(':')
    if len(arr) != 2:
        return

    strip_index = int(arr[0])
    strip_config = strips.get(strip_index)
    strip = strip_config.get('neopixel')
    led_index = int(arr[1])
    if (last_set_colors.get(led_code) == color):
        return
    
    last_color = last_set_colors.get(led_code)
    if (last_color is None):
        last_color = 0x000000
    last_set_colors[led_code] = color
    if strip_index == 2:
        print('{} is being set to {}'.format(led_code, color))
    if strip is not None:
        strip[led_index] = color
        time.sleep(light_set_delay)
    # print('\tPixel {} is set to {}'.format(led_index, color))
        

def filter_led_config_direction(arr, direction_id):
    for item in arr:
        if item.get('direction') == direction_id:
            return item
    return None

def find_stop_by_stop_code(arr, stop_code):
    for item in arr:
        if item.get('code') == int(stop_code):
            return item
    return None

def get_stop_config_by_stop_code(route_short_name, direction, stop_code):
    line_directions = led_config.get(route_short_name)
    if line_directions is None:
        return None
    directional_stops = filter_led_config_direction(line_directions, direction)
    if (directional_stops is None):
        return None
    return find_stop_by_stop_code(directional_stops.get('stops'), stop_code)

def get_prev_stop_config_by_current_stop_code(route_short_name, direction, stop_code):
    line_directions = led_config.get(route_short_name)
    if line_directions is None:
        return None
    directional_stops = filter_led_config_direction(line_directions, direction)
    if (directional_stops is None):
        return None
    arr = directional_stops.get('stops')
    for index, item in enumerate(arr):
        if item.get('code') == stop_code:
            return None if index == 0 else arr[index - 1]


all_route_trips_by_id = {}
stops_by_id = {}
config_stops = {}

def get_trips():
    for route_name in led_config:
        result = api_call_with_retry(
            client.trips_for_route.list,
            route_name,
            include_schedule=True,
            include_status=True
        )
        if result is None or result.data is None:
            print(f"{Fore.RED}Failed to get trips for route {route_name} after retries{Style.RESET_ALL}")
            continue
        trips = result.data.references.trips
        for trip in trips:
            all_route_trips_by_id[trip.id] = trip



def hydrate_routes():
    hydrated_routes = {}
    for route_name in led_config:
        result = api_call_with_retry(client.route.retrieve, route_name)
        if result is None or result.data is None:
            print(f"{Fore.RED}Failed to get route info for {route_name} after retries{Style.RESET_ALL}")
            continue

        route = result.data.entry
        hydrated_routes[route_name] = route
        route.stops = {}
    get_trips()

    return hydrated_routes


def initialize_with_retry(max_attempts=5, retry_delay=10):
    """
    Try to initialize routes with retries.
    If API is temporarily down, wait and retry instead of crashing.
    """
    for attempt in range(max_attempts):
        routes = hydrate_routes()
        if routes:
            return routes
        print(f"{Fore.YELLOW}No routes loaded, retrying initialization ({attempt + 1}/{max_attempts})...{Style.RESET_ALL}")
        time.sleep(retry_delay)

    print(f"{Fore.RED}Failed to initialize routes after {max_attempts} attempts. Exiting.{Style.RESET_ALL}")
    raise SystemExit(1)


routes_by_id = initialize_with_retry()
trips_by_id = {}
clear_lights()

def get_latest_feed():
    trips_by_id.clear()
    vehicles_by_route = {}

    for idx, route_id in enumerate(routes_by_id):
        routes_by_id[route_id].trips = {}
        route_trips_result = api_call_with_retry(
            client.trips_for_route.list,
            route_id,
            include_status=True,
            include_schedule=True
        )
        if route_trips_result is None or route_trips_result.data is None:
            print(f"{Fore.YELLOW}Skipping route {route_id} - API call failed{Style.RESET_ALL}")
            vehicles_by_route[route_id] = []
            continue

        route_trips = route_trips_result.data.list
        trip_lookup = {}
        for trip in route_trips_result.data.references.trips:
            trip_lookup[trip.id] = trip
        vehicles_by_route[route_id] = []
        for route_trip in route_trips:
            trips_by_id[route_trip.trip_id] = route_trip
            routes_by_id[route_id].trips[route_trip.trip_id] = route_trip
            trip = trip_lookup[route_trip.trip_id]
            route_trip.direction = int(trip.direction_id)
            vehicles_by_route[route_id].append({
                'vehicle': route_trip.status,
                'route': routes_by_id[route_id],
                'trip': route_trip
            })

    return vehicles_by_route


def get_all_route_stops(route_short_name):
    line_directions = led_config.get(route_short_name)
    if line_directions is None:
        return None
    all_stops = []
    for directional_config in line_directions:
        direction_stops = directional_config.get('stops')
        for stop in direction_stops:
            all_stops.append(stop)
    return all_stops

def parse_color(color_str):
    color = '0x{}'.format(color_str)
    return int(color, 0)

def get_route_config(route_name, direction):
    route_config = led_config.get(route_name)
    for direction_config in route_config:
        if direction == direction_config.get('direction'):
            return direction_config


def get_route_stop_config(route_name, direction, stop_code):
    route_config = led_config.get(route_name)
    for direction_config in route_config:
        if direction == direction_config.get('direction'):
            for stop in direction_config.get('stops'):
                if stop.get('code') == stop_code:
                    return stop
                
def get_led_for_intermediary(stop, vehicle):
    intermediaries = stop.get('intermediaries')
    if intermediaries is None:
        return None
    for intermediate in intermediaries.get('features'):
        geometry_json = intermediate.get('geometry')
        coords = geometry_json.get('coordinates').copy()

        polygon = Polygon(LinearRing(coords))
        point = Point(vehicle.position.lon, vehicle.position.lat)
        is_inside = polygon.contains(point)
        if is_inside:
            return intermediate.get('led')
        
def print_vehicle_status(vehicle, is_at_stop, trip, stop, color):
    at_message = "Stopped" if is_at_stop else "En Route"
    direction = "↑" if trip.direction == 1 else "↓"
    print_colored('{}|{}|{}|{}|{},{}'.format(direction, at_message, stop.get('name'), vehicle.vehicle_id, vehicle.position.lat, vehicle.position.lon), color)

while(True):
    if not DEBUG_MODE:
        cls()
    vehicles_by_route = get_latest_feed()

    vehicles_set_this_iteration = {}
    for route_short_name in led_config:
        vehicles = vehicles_by_route.get(route_short_name)

        for vehicle_item in vehicles:
            vehicle = vehicle_item.get('vehicle')
            if (vehicle is None):
                continue
            route: Route = vehicle_item.get('route')
            trip = vehicle_item.get('trip')
            next_stop_id = vehicle.next_stop

            stop = get_route_stop_config(route_short_name, trip.direction, next_stop_id)
            if stop is None:
                print('WARN Stop {} was not found in config, direction {}'.format(next_stop_id, trip.direction))
                continue
            if (stop.get('lat') is None) or (stop.get('lon') is None):
                print(f'WARN: Stop {stop.get("code")} has malformatted config, direction {trip.direction}')


            stop_bounding_area = BoundingArea.FromPoint(stop.get('lat'), stop.get('lon'), stop_radius)
            vehicle_is_at_stop = stop_bounding_area.contains(vehicle.position.lat, vehicle.position.lon)
            route_config = get_route_config(route_short_name, trip.direction)
            color_raw = route_config.get('color')
            color = parse_color(color_raw)
            if stop is not None:
                if vehicle_is_at_stop:
                    print_vehicle_status(vehicle, vehicle_is_at_stop, trip, stop, color)
                    set_single_led(stop.get('led'), color)
                    vehicles_set_this_iteration[stop.get('led')] = True
                else:

                    # Calculate the distance from the last stop to this one
                    trip_meta = all_route_trips_by_id.get(trip.trip_id)
                    if (trip_meta is None):
                        # New trip added
                        get_trips()
                        trip_meta = all_route_trips_by_id.get(trip.trip_id)
                        if trip_meta is None:
                            print ('WARN - Vehicle {} has no trip metadata')
                    schedule = trip.schedule.stop_times

                    

                    prev_stop = None
                    for idx, possible_prev_stop in enumerate(schedule):
                        if (len(schedule) > idx + 1 and schedule[idx + 1].stop_id == stop.get('code')):
                            prev_stop = possible_prev_stop
                    

                    prev_stop_config = get_prev_stop_config_by_current_stop_code(route.id, int(trip_meta.direction_id), stop.get('code'))
                    if (prev_stop_config is None):
                        continue

                    led = get_led_for_intermediary(prev_stop_config, vehicle)
                    
                    # We know we're not at the stop, now just figure out which light to light up
                    if led is not None and led != "":
                        print_vehicle_status(vehicle, vehicle_is_at_stop, trip, stop, color)
                        set_single_led(led, color)
                        vehicles_set_this_iteration[led] = True
                    else:
                        print_colored('Unknown location! Vehicle {} is heading to stop {} (direction {}) ({}, {})'.format(vehicle.vehicle_id, stop.get('name'), trip_meta.direction_id, vehicle.position.lat, vehicle.position.lon), 0xffff00)
        # clear_lights()
    route_stops = get_all_route_stops(route_short_name)
    
    stop_lookup = {}
    disabled = {}
    for route_name in led_config:
        route_direction = led_config.get(route_name)
        for route in route_direction:
            stops = route.get('stops')
            for stop in stops:
                stop_lookup[stop.get('led')] = True
                if stop.get('disabled'):
                    disabled[stop.get('led')] = True
    
    for strip_config_idx in strips.keys():
        strip_config = strips[strip_config_idx]
        strip = strip_config.get('neopixel')
        led_count = strip_config.get('length')
        for i in range(led_count):
            led = '{}:{}'.format(strip_config_idx, i)
            if vehicles_set_this_iteration.get(led) is not True:
                if stop_lookup.get(led) is None:
                    clear_single_led(led)
                elif disabled.get(led) is not None:
                    set_single_led(led, LightStatus.DISABLED_STATION)
                else:
                    set_single_led(led, LightStatus.STATION)

    if DEBUG_MODE:
        render_leds()

    time.sleep(loop_sleep)

