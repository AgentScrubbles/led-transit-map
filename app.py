
from transit import TransitFeed, Route, Vehicle, Stop, Trip
from strip_config import LightStop
import os
import time

static_url = 'https://metro.kingcounty.gov/GTFS/google_transit.zip'
realtime_url = 'https://s3.amazonaws.com/kcm-alerts-realtime-prod/vehiclepositions.pb'
local_path = '/tmp/gtfs'

os.makedirs(os.path.dirname(local_path), exist_ok=True)


t = TransitFeed(static_url, realtime_url, local_path)


t.GetStaticFeed()
t.ParseStaticFeed()



# stops = route.GetOrderedStops()

strip = [
    LightStop(t.GetStop(123))
]



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


while(True):
    routes = t.GetCurrentStatus()

    route: Route = routes['E Line']
    for trip in route.trips.values():
        if (trip.direction_id == 0):
            direction0 = trip
        if trip.direction_id == 1:
            direction1 = trip

    vehicles: list[Vehicle] = route.GetVehicles()

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

