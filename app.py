
from transit import TransitFeed, Route, Vehicle, Stop, Trip
from strip_config import LightStop, StripConfig, LightStatus
import os
import time
import board
import neopixel



static_url = 'https://metro.kingcounty.gov/GTFS/google_transit.zip'
realtime_url = 'https://s3.amazonaws.com/kcm-alerts-realtime-prod/vehiclepositions.pb'
local_path = '/tmp/gtfs'
pixels = neopixel.NeoPixel(board.D10, 10)
light_colors = {
    LightStatus.EMPTY: (0, 0, 0),
    LightStatus.STATION: (255, 213, 0),
    LightStatus.OCCUPIED: (95, 173, 40)
}

os.makedirs(os.path.dirname(local_path), exist_ok=True)


t = TransitFeed(static_url, realtime_url, local_path)

pixels.fill((0, 255, 0))
t.GetStaticFeed()
t.ParseStaticFeed()
pixels.fill((0, 0, 0))

# stops = route.GetOrderedStops()
routes = t.GetCurrentStatus()
strip = [
    LightStop(t.GetStop(538), 0),
    LightStop(t.GetStop(558), 2),
    LightStop(t.GetStop(575), 4),
    LightStop(t.GetStop(600), 6),
    LightStop(t.GetStop(605), 9),
]

strip = StripConfig(strip)

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

def write_status_to_strip(statuses: list[LightStatus]):
    pixels.fill((0, 0, 0))
    for index, status in enumerate(statuses):
        print('Getting color for {}', status.value)
        color = light_colors.get(status.value)
        print('Setting idx {} to color {}', index, color)
        pixels[index] = color

while(True):
    routes = t.GetCurrentStatus()

    route: Route = routes['E Line']
    for trip in route.trips.values():
        if (trip.direction_id == 0):
            direction0 = trip
        if trip.direction_id == 1:
            direction1 = trip

    vehicles: list[Vehicle] = route.GetVehicles()

    statuses = strip.calculate_strip(vehicles)
    write_status_to_strip(statuses)

    direction0Occupied = {}
    direction1Occupied = {}

    for vehicle in vehicles:
        trip: Trip = route.GetTrip(vehicle.trip_id)
        trip_stops = trip.GetTripStops()
        trip_stop = trip_stops.get(vehicle.stop_id)
        if (trip.direction_id == 0):
            direction0Occupied[vehicle.stop_id] = True
        if (trip.direction_id == 1):
            direction1Occupied[vehicle.stop_id] = True

    stopStatusDirection0 = []
    stopStatusDirection1 = []

    for stop_id in direction0.GetTripStops():
        occupiedStop = direction0Occupied.get(stop_id) is True
        stopStatusDirection0.append(occupiedStop)

    for stop_id in direction1.GetTripStops():
        occupiedStop = direction1Occupied.get(stop_id) is True
        stopStatusDirection1.append(occupiedStop)

    printStops(stopStatusDirection0)
    printStops(stopStatusDirection1)
    print()
    time.sleep(2)

