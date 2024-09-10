
from transit import Route, Vehicle, Stop, Trip
from strip_config import LightStop, StripConfig, LightStatus, BoundingArea
import os
import time
import board
import neopixel
import sqlite3
import json
import asyncio
from shapely.geometry import Polygon, Point, LinearRing
from numpy import * 

from onebusaway import OnebusawaySDK
from dotenv import main

main.load_dotenv()

client = OnebusawaySDK(
    api_key=os.getenv("ONEBUSAWAY_API_KEY")
)

COUNT_LED = 160 # todo, need to do this per strip later
static_url = 'https://metro.kingcounty.gov/GTFS/google_transit.zip'
realtime_url = os.getenv('realtime_url')
agency = int(os.getenv('AGENCY_ID'))
last_set_colors = {}
conn = sqlite3.connect(os.getenv('gtfs_db'))
stop_radius = 0.01
loop_sleep = 4

# 2 line #0x00A0DF
local_path = '/tmp/gtfs'
# pixels = neopixel.NeoPixel(board.D10, 10)
light_colors = {
    LightStatus.EMPTY: 0x000000,
    LightStatus.STATION: 0xFFFF00,
    LightStatus.OCCUPIED: 0x3DAE2B
}
with open('strips.json') as json_data:
    led_config = json.load(json_data)
os.makedirs(os.path.dirname(local_path), exist_ok=True)

strips= {
    1: neopixel.NeoPixel(board.D18, COUNT_LED, brightness=0.1),
    2: neopixel.NeoPixel(board.D10, COUNT_LED, brightness=0.2, pixel_order=neopixel.GRB)
}

neopixel.NeoPixel(board.D10, COUNT_LED, brightness=0.1).fill(0xc003e0)


def printStops(stopArr):
    str = '['
    occupiedArr = []
    for stopOccupiedBool in stopArr:
        if stopOccupiedBool:
            occupiedArr.append('X')
        else:
            occupiedArr.append(' ')
    str = '[ ' + '|'.join(occupiedArr) + ' ]'
    print(str)

def clear_lights():
    color = light_colors.get(LightStatus.EMPTY)
    for strip_idx in strips:
        strip = strips.get(strip_idx)
        if (strip is not None):
            strip.fill(color)

def clear_single_led(led_code: str):
    set_single_led(led_code, 0x000000)


async def fade_led(strip, led_index, start_color, end_color, fade_duration=500, step_duration=50):
    # Ensure durations are valid
    fade_duration = max(fade_duration, step_duration)
    
    # Number of steps
    steps = fade_duration // step_duration
    
    # Extract RGB components of start and end colors
    start_r = (start_color >> 16) & 0xFF
    start_g = (start_color >> 8) & 0xFF
    start_b = start_color & 0xFF
    
    end_r = (end_color >> 16) & 0xFF
    end_g = (end_color >> 8) & 0xFF
    end_b = end_color & 0xFF
    
    # Compute RGB differences
    r_step = (end_r - start_r) / steps
    g_step = (end_g - start_g) / steps
    b_step = (end_b - start_b) / steps
    
    for step in range(steps + 1):
        # Calculate the current color
        r = int(start_r + r_step * step)
        g = int(start_g + g_step * step)
        b = int(start_b + b_step * step)
        
        # Combine into a single hex value
        current_color = (r << 16) | (g << 8) | b
        
        # Set the LED color
        if strip is not None:
            strip[led_index] = current_color
        
        # Wait for the next step
        await asyncio.sleep(step_duration)  # Convert ms to seconds

def hex_to_rgb(hex_color):
    # Extract the red, green, and blue components from the hex color
    r = (hex_color >> 16) & 0xFF  # Extract the first 8 bits (red)
    g = (hex_color >> 8) & 0xFF   # Extract the next 8 bits (green)
    b = hex_color & 0xFF          # Extract the last 8 bits (blue)
    
    return (r, g, b)


def set_single_led(led_code: str, status_or_color):

    if isinstance(status_or_color, LightStatus):
        color = light_colors.get(status_or_color)
    else:
        color = status_or_color
    color = hex_to_rgb(color)
    arr = led_code.split(':')
    strip_index = int(arr[0])
    strip = strips.get(strip_index)
    led_index = int(arr[1])
    if (last_set_colors.get(led_code) == color):
        return
    
    last_color = last_set_colors.get(led_code)
    if (last_color is None):
        last_color = 0x000000
    last_set_colors[led_code] = color
    if strip is not None:
        adjusted_color = strip.gamma32(neopixel.Color(color))
        strip[led_index] = adjusted_color
        # strip.setPixelColor(0, *strip.gamma32(neopixel.Color(color)))
        # strip[led_index] = color
        # asyncio.run(fade_led(strip, led_index, last_color, color, step_duration=50))
    print('\tPixel {} is set to {}'.format(led_index, color))
        

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
        trips = client.trips_for_route.list(route_name, include_schedule=True, include_status=True).data.references.trips
        for trip in trips:
            all_route_trips_by_id[trip.id] = trip



def hydrate_routes():
    hydrated_routes = {}
    for route_name in led_config:
        route = client.route.retrieve(route_name).data.entry
        
        hydrated_routes[route_name] = route
        route.stops = {}
        # route_conf = led_config.get(route_name)
        # for direction_conf in route_conf:
        #     stops = direction_conf.get('stops')
        #     for stop in stops:
        #         stops_by_id[stop.get('code')] = stop
    get_trips()

    return hydrated_routes

routes_by_id = hydrate_routes()
trips_by_id = {}
clear_lights()

def get_latest_feed():
    trips_by_id.clear()
    vehicles_by_route = {}
    
    for idx, route_id in enumerate(routes_by_id):
        routes_by_id[route_id].trips = {}
        route_trips_result = client.trips_for_route.list(route_id, include_status=True, include_schedule=True)
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

def get_route_stop_config(route_name, direction, stop_code):
    route_config = led_config.get(route_short_name)
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
        # coords.append(coords[0])
        

        polygon = Polygon(LinearRing(coords))
        point = Point(vehicle.position.lon, vehicle.position.lat)
        is_inside = polygon.contains(point)
        if is_inside:
            return intermediate.get('led')
        

while(True):

    vehicles_by_route = get_latest_feed()

    # pixels.fill((0, 0, 0))

    for route_short_name in led_config:
        vehicles = vehicles_by_route.get(route_short_name)

        vehicles_set_this_iteration = {}

        for vehicle_item in vehicles:
            vehicle = vehicle_item.get('vehicle')
            route: Route = vehicle_item.get('route')
            trip = vehicle_item.get('trip')
            next_stop_id = vehicle.next_stop

            stop = get_route_stop_config(route_short_name, trip.direction, next_stop_id)
            if stop is None:
                print('WARN Stop {} was not found in config, direction {}'.format(next_stop_id, trip.direction))
                continue

            stop_bounding_area = BoundingArea.FromPoint(stop.get('lat'), stop.get('lon'), stop_radius)
            vehicle_is_at_stop = stop_bounding_area.contains(vehicle.position.lat, vehicle.position.lon)
            if stop is not None:
                if vehicle_is_at_stop:
                    print('Vehicle {} is at stop {}'.format(vehicle.vehicle_id, stop.get('name')))
                    set_single_led(stop.get('led'), parse_color(route.color))
                    vehicles_set_this_iteration[stop.get('led')] = True
                else:

                    if trip.direction == 1:
                        print ('Ignoring direction 1')
                        continue

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
                    print('Vehicle {} is heading to stop {} ({}, {})'.format(vehicle.vehicle_id, stop.get('name'), vehicle.position.lat, vehicle.position.lon))
                    # We know we're not at the stop, now just figure out which light to light up
                    if led is not None:
                        set_single_led(led, parse_color(route.color))
                        vehicles_set_this_iteration[led] = True
        # clear_lights()
        route_stops = get_all_route_stops(route_short_name)
        
        stop_lookup = {}
        for route_name in led_config:
            route_direction = led_config.get(route_name)
            for route in route_direction:
                stops = route.get('stops')
                for stop in stops:
                    stop_lookup[stop.get('led')] = True
        
        for strip in strips:
            for i in range(COUNT_LED):
                led = '{}:{}'.format(strip, i)
                if vehicles_set_this_iteration.get(led) is not True:
                    if stop_lookup.get(led) is None:
                        clear_single_led(led)
                    else:
                        set_single_led(led, LightStatus.STATION)


    time.sleep(loop_sleep)

