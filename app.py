
from transit import TransitFeed, Route, Vehicle, Stop, Trip
from strip_config import LightStop, StripConfig, LightStatus, BoundingArea
import os
import time
# import board
# import neopixel
import sqlite3
import pandas as pd
from google.transit import gtfs_realtime_pb2
import requests
from protobuf_to_dict import protobuf_to_dict
from flatten_json import flatten
import json

static_url = 'https://metro.kingcounty.gov/GTFS/google_transit.zip'
realtime_url = 'https://s3.amazonaws.com/kcm-alerts-realtime-prod/vehiclepositions.pb'

conn = sqlite3.connect('/tmp/kcmetro.db')

local_path = '/tmp/gtfs'
# pixels = neopixel.NeoPixel(board.D10, 10)
light_colors = {
    LightStatus.EMPTY: (0, 0, 0),
    LightStatus.STATION: (255, 213, 0),
    LightStatus.OCCUPIED: (95, 173, 40)
}
with open('strips.json') as json_data:
    led_config = json.load(json_data)
os.makedirs(os.path.dirname(local_path), exist_ok=True)

strips= {
    1: None # Here is where the pixels will go
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
            strip = color

def set_single_led(led_code: str, status: LightStatus):
    color = light_colors.get(status)
    arr = led_code.split(':')
    strip_index = int(arr[0])
    strip = strips.get(strip_index)
    led_index = int(arr[1])
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

def get_route_by_id(route_id):
    route_df = pd.read_sql_query("SELECT * FROM routes r where r.route_id = '{}'".format(route_id), conn)
    return Route(route_df.iloc[0])

def get_route_by_name(name):
    route_df = pd.read_sql_query("SELECT * FROM routes r where r.route_short_name = '{}'".format(name), conn)
    return Route(route_df.iloc[0])

def get_trip_by_id(trip_id):
    trip_df = pd.read_sql_query("SELECT * FROM trips t where t.trip_id = '{}'".format(trip_id), conn)
    return Trip(trip_df.iloc[0])

def get_stops_by_route_id(route_id):
    stops_df = pd.read_sql_query("SELECT s.* FROM routes r JOIN route_stops rs ON rs.route_id = r.route_id JOIN stops s ON rs.stop_id = s.stop_id WHERE r.route_id = {}".format(route_id), conn)
    stops = []
    for stop_idx, stop in stops_df.iterrows():
        stops.append(Stop(stop))
    return stops

def hydrate_routes():
    hydrated_routes = {}
    for route_name in led_config:
        route = get_route_by_name(route_name)
        route_id = int(route.id)
        hydrated_routes[route_id] = route
        stops = get_stops_by_route_id(route_id)
        route.SetStops(stops)

    return hydrated_routes

routes_by_id = hydrate_routes()

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

def get_latest_feed():
    feed = gtfs_realtime_pb2.FeedMessage()
    response = requests.get(realtime_url, allow_redirects=True)
    feed.ParseFromString(response.content)

    dict = protobuf_to_dict(feed)

    zet_df = pd.DataFrame(flatten(record, '.')
        for record in dict['entity'])

    vehicles_by_route = {}
    for index, row in zet_df.iterrows():
        vehicle = Vehicle(row)

        route: Route = routes_by_id.get(vehicle.route_id)
        # We don't care about this route
        if route is None:
            continue
        trip = get_trip_by_id(int(vehicle.trip_id))
        route_vehicles = vehicles_by_route.get(route.short_name)
        if (route_vehicles is None):
            vehicles_by_route[route.short_name] = []
            route_vehicles = vehicles_by_route.get(route.short_name)

        route_vehicles.append({
            "route": route,
            "trip": trip,
            "vehicle": vehicle
        })
    return vehicles_by_route




while(True):

    vehicles_by_route = get_latest_feed()

    # pixels.fill((0, 0, 0))

    for route_short_name in led_config:
        route_config = led_config.get(route_short_name)
        vehicles = vehicles_by_route.get(route_short_name)

        clear_lights()

        route_stops = get_all_route_stops(route_short_name)
        for route_stop in route_stops:
            set_single_led(route_stop.get('led'), LightStatus.STATION)

        for vehicle_item in vehicles:
            vehicle: Vehicle = vehicle_item.get('vehicle')
            route: Route = vehicle_item.get('route')
            stop: Stop = route.stops.get(vehicle.stop_id)
            stop_bounding_area = BoundingArea.FromPoint(stop.latitude, stop.longitude, 0.05)
            vehicle_is_at_stop = stop_bounding_area.contains(vehicle.latitude, vehicle.longitude)
            stop_config = get_stop_config_by_stop_code(route.short_name, vehicle.direction_id, stop.code)
            label = 'is at' if vehicle_is_at_stop else 'is heading to'
            if stop_config is not None:
                print('Vehicle {} {} stop {}'.format(vehicle.label, label, stop.name))
                set_single_led(stop_config.get('led'), LightStatus.OCCUPIED)

    time.sleep(2)

