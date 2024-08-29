
from transit import TransitFeed, Route, Vehicle, Stop, Trip
from strip_config import LightStop, StripConfig, LightStatus, BoundingArea
import os
import time
import board
# import neopixel_spi
import sqlite3
import pandas as pd
from google.transit import gtfs_realtime_pb2
import requests
from protobuf_to_dict import protobuf_to_dict
from flatten_json import flatten
import json
import enum

from onebusaway import OnebusawaySDK
from dotenv import main

main.load_dotenv()

client = OnebusawaySDK(
    api_key=os.getenv("ONEBUSAWAY_API_KEY")
)


static_url = 'https://metro.kingcounty.gov/GTFS/google_transit.zip'
realtime_url = os.getenv('realtime_url')
agency = int(os.getenv('AGENCY_ID'))
last_set_colors = {}
conn = sqlite3.connect(os.getenv('gtfs_db'))
stop_radius = 0.01
loop_sleep = 8

# 2 line #0x00A0DF
local_path = '/tmp/gtfs'
# pixels = neopixel.NeoPixel(board.D10, 10)
light_colors = {
    LightStatus.EMPTY: 0x000000,
    LightStatus.STATION: 0xFFD700,
    LightStatus.OCCUPIED: 0x3DAE2B
}
with open('strips.json') as json_data:
    led_config = json.load(json_data)
os.makedirs(os.path.dirname(local_path), exist_ok=True)

strips= {
    1: None #neopixel_spi.NeoPixel_SPI(board.SPI(), 100, brightness=0.1)
}


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
            pass
        #    strip.fill(color)

def set_single_led(led_code: str, status_or_color):

    if isinstance(status_or_color, LightStatus):
        color = light_colors.get(status_or_color)
    else:
        color = status_or_color
    arr = led_code.split(':')
    strip_index = int(arr[0])
    strip = strips.get(strip_index)
    led_index = int(arr[1])
    if (last_set_colors.get(led_code) == color):
        return
    last_set_colors[led_code] = color
    if strip is not None:
        strip[led_index] = color
        

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
        route_conf = led_config.get(route_name)
        for direction_conf in route_conf:
            stops = direction_conf.get('stops')
            for stop in stops:
                stops_by_id[stop.get('code')] = stop
    get_trips()


        # stop_ids = client.stops_for_route.list(route_name).data.entry.stop_ids
        # for stop_id in stop_ids:
        #     stop_detail = client.stop.retrieve(stop_id).data.entry
        #     print('{},{},{},{}'.format(stop_detail.id, stop_detail.name, stop_detail.lat, stop_detail.lon))
        #     route.stops[stop_id] = stop_detail
        # route.SetStops(stops)

    return hydrated_routes

routes_by_id = hydrate_routes()
trips_by_id = {}

def get_latest_feed():
    trips_by_id.clear()
    vehicles_by_route = {}
    
    for idx, route_id in enumerate(routes_by_id):
        routes_by_id[route_id].trips = {}
        route_trips = client.trips_for_route.list(route_id, include_status=True).data.list
        vehicles_by_route[route_id] = []
        for route_trip in route_trips:
            trips_by_id[route_trip.trip_id] = route_trip
            routes_by_id[route_id].trips[route_trip.trip_id] = route_trip
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

def find_largest_object(objects, target_percentage):
    # Initialize the best object and best percentage
    best_object = None
    best_percentage = -1
    closest_object = None
    
    for obj in objects:
        led_percentage = float(obj.get('percentage'))
        
        # Track the closest object if no valid one is found
        if closest_object is None or led_percentage < closest_object.get('percentage'):
            closest_object = obj
        
        if led_percentage <= target_percentage:
            if led_percentage > best_percentage:
                best_object = obj
                best_percentage = led_percentage
    
    # If no object was found within the target, return the closest one
    return best_object if best_object else closest_object


while(True):

    vehicles_by_route = get_latest_feed()

    # pixels.fill((0, 0, 0))

    for route_short_name in led_config:
        route_config = led_config.get(route_short_name)
        vehicles = vehicles_by_route.get(route_short_name)

        vehicles_set_this_iteration = {}

        for vehicle_item in vehicles:
            vehicle = vehicle_item.get('vehicle')
            route: Route = vehicle_item.get('route')
            trip = vehicle_item.get('trip')
            next_stop_id = vehicle.next_stop
            stop = stops_by_id.get(next_stop_id)
            stop_bounding_area = BoundingArea.FromPoint(stop.get('lat'), stop.get('lon'), stop_radius)
            vehicle_is_at_stop = stop_bounding_area.contains(vehicle.position.lat, vehicle.position.lon)
            if stop is not None:
                if vehicle_is_at_stop:
                    print('Vehicle {} is at stop {}'.format(vehicle.vehicle_id, stop.get('name')))
                    set_single_led(stop.get('led'), parse_color(route.color))
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
                    prev_bounding_area = BoundingArea.FromPoint(prev_stop_config.get('lat'), prev_stop_config.get('lon'), stop_radius)
                    percentage = stop_bounding_area.calculate_percentage(prev_bounding_area, (vehicle.position.lat, vehicle.position.lon))
                    print('Vehicle {} is heading to stop {} ({}%)'.format(vehicle.vehicle_id, stop.get('name'), round(percentage * 100)))
                    # We know we're not at the stop, now just figure out which light to light up
                    led = find_largest_object(stop.get('loading'), percentage)
                    if led is not None:
                        set_single_led(led.get('led'), parse_color(route.color))
                        vehicles_set_this_iteration[stop.get('led')] = True
        # clear_lights()
        route_stops = get_all_route_stops(route_short_name)
        for route_stop in route_stops:
            led = route_stop.get('led')
            if vehicles_set_this_iteration.get(led) is not True:
                set_single_led(led, LightStatus.STATION)
    time.sleep(loop_sleep)

