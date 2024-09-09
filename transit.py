import pandas as pd

def print_stopwatch(sec, msg):
  mins = sec // 60
  sec = sec % 60
  hours = mins // 60
  mins = mins % 60
  print("{0} = {1}:{2}:{3}".format(msg, int(hours),int(mins),sec))

class Vehicle:
    def __init__(self, row):
        self.id = row.get('id')
        self.trip_id = row.get('vehicle.trip.trip_id')
        self.start_date = row.get('vehicle.trip.start_date')
        self.route_id = row.get('vehicle.trip.route_id')
        self.direction_id = row.get('vehicle.trip.direction_id')
        self.latitude = row.get('vehicle.position.latitude')
        self.longitude = row.get('vehicle.position.longitude')
        self.stop_sequence = row.get('vehicle.current_stop_sequence')
        self.timestamp = row.get('vehicle.timestamp')
        try:
            self.stop_id = int(row.get('vehicle.stop_id'))
        except:
            print()
        self.vehicle_id = row.get('vehicle.vehicle.id')
        self.label = row.get('vehicle.vehicle.label')
        # self.bearing = row.get('vehicle.position.bearing')
        self.speed = row.get('vehicle.position.speed')
        self.status = row.get('vehicle.current_status')

class TripStop:
    def __init__(self, row):
        self.trip_id = row.get('trip_id')
        self.arrival_time = row.get('arrival_time')
        self.departure_time = row.get('departure_time')
        self.stop_id = int(row.get('stop_id'))
        self.stop_sequence = row.get('stop_sequence')
        self.stop_headsign = row.get('stop_headsign')
        self.pickup_type = row.get('pickup_type')
        self.drop_off_type = row.get('drop_off_type')
        self.shape_dist_traveled = row.get('shape_dist_traveled')
        self.timepoint = row.get('timepoint')

class Stop:
    def __init__(self, row):
        self.id = row.get('stop_id')
        self.code = row.get('stop_code')
        self.name = row.get('stop_name')
        self.description = row.get('stop_desc')
        self.latitude = row.get('stop_lat')
        self.longitude = row.get('stop_lon')
        self.zone_id = row.get('zone_id')
        self.stop_url = row.get('stop_url')
        self.location_type = row.get('location_type')
        self.parent_station = row.get('parent_station')
        self.timezone = row.get('stop_timezone')
        self.wheelchair = row.get('wheelchair_boarding')

    def IsVehicleAtStop(self, vehicle: Vehicle):
        return vehicle.stop_id == self.id
    
    def AreVehiclesAtStop(self, vehicles: list):
        for vehicle in vehicles:
            if self.IsVehicleAtStop(vehicle):
                return True
        return False


class Trip:
    def __init__(self, row):
        self.vehicles = []
        self.trip_stops = {}
        self.id = row.get('trip_id')
        self.route_id = row.get('route_id')
        self.service_id = row.get('service_id')
        self.headsign = row.get('trip_headsign')
        self.short_name = row.get('trip_short_name')
        self.direction_id = row.get('direction_id')
        self.block_id = row.get('block_id')
        self.shape_id = row.get('shape_id')
        self.peak = row.get('peak_flag')
        self.fare_id = row.get('fare_id')
        self.wheelchair = row.get('wheelchair_accessible')
        self.bikes = row.get('bikes_allowed')

    def AddStop(self, trip_stop: TripStop):
        self.trip_stops[trip_stop.stop_id] = trip_stop

    def AddVehicle(self, vehicle: Vehicle):
        self.vehicles.append(vehicle)
    
    def GetVehicles(self):
        return self.vehicles
    
    def GetTripStops(self):
        return self.trip_stops.copy()
    
    def ClearVehicles(self):
        self.vehicles.clear()

class Route:

    def __init__(self, row):
        self.trips = {}
        self.stops = {}
        self.id = row.get('route_id')
        self.agency_id = row.get('agency_id')
        self.short_name = row.get('route_short_name')
        self.long_name = row.get('route_long_name')
        self.description = row.get('route_desc')
        self.type = row.get('route_type')
        self.url = row.get('route_url')
        self.color = row.get('route_color')
        self.text_color = row.get('route_text_color'),

    def ClearVehicles(self):
        for trip in self.trips.values():
            trip.ClearVehicles()

    def AddTrip(self, trip: Trip):
        self.trips[trip.id] = trip

    def AddStop(self, stop: Stop):
        self.stops[stop.id] = stop

    def SetStops(self, stops: list[Stop]):
        for stop in stops:
            self.stops[stop.id] = stop

    def GetStops(self):
        return self.stops.copy()

    def GetTrip(self, trip_id):
        return self.trips.get(trip_id)
    
    def GetVehicles(self):
        vehicles = []
        for trip in self.trips.values():
            for vehicle in trip.GetVehicles():
                vehicles.append(vehicle)
        return vehicles
    
    def GetOrderedStops(self):
        keysSorted = sorted(self.stops.keys())
        stopsSorted = []
        for key in keysSorted:
            stopsSorted.append(self.stops[key])
        return stopsSorted
