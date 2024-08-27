from transit import Stop, Vehicle
import math
from enum import Enum

class LightStatus(Enum):
    EMPTY = 0,
    STATION = 1,
    OCCUPIED = 2

class BoundingArea:
    def __init__(self, x1: float, y1: float, x2: float, y2: float):
        self.X1 = x1
        self.Y1 = y1
        self.X2 = x2
        self.Y2 = y2

    def contains(self, px, py) -> bool:
        # Check if the point lies within the bounding area
        return self.X1 <= px <= self.X2 and self.Y1 <= py <= self.Y2

    def toString(self):
        return '{},{} - {},{}'.format(self.X1, self.Y1, self.X2, self.Y2)


    @staticmethod
    def FromPoint(x: float, y: float, offset: float):
        from_center_offset = offset / 2
        x1 = x - from_center_offset
        y1 = y - from_center_offset
        x2 = x + from_center_offset
        y2 = y + from_center_offset
        return BoundingArea(x1, y1, x2, y2)
    
    def distance(self, x1, y1, x2, y2):
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def calculate_percentage(self, area2, point: tuple):
        # Unpack point coordinates
        px, py = point

        # Calculate the relevant edges:
        # For area1, use the farthest edge in the direction of area2
        # For area2, use the closest edge in the direction from area1
        
        # Assuming that the two BoundingAreas are aligned (i.e., area2 is always to the right and downwards of area1):
        area1_edge_x = self.X2  # Right edge of the first area
        area1_edge_y = self.Y2  # Bottom edge of the first area
        area2_edge_x = area2.X1  # Left edge of the second area
        area2_edge_y = area2.Y1  # Top edge of the second area

        # Calculate total distance between edges
        total_distance = self.distance(area1_edge_x, area1_edge_y, area2_edge_x, area2_edge_y)

        # Calculate distance from area1 edge to the point
        distance_to_point = self.distance(area1_edge_x, area1_edge_y, px, py)

        # Calculate the percentage as a ratio of these distances
        percentage = distance_to_point / total_distance

        # Ensure the percentage is between 0 and 1
        return max(0, min(1, percentage))

class LightStop:
    def __init__(self, stop: Stop, light_index: int) -> None:
        self.stop = stop
        self.light_index = light_index
        self.bounding = BoundingArea.FromPoint(self.stop.latitude, self.stop.longitude, 0.1)

    def is_vehicle_in_stop(self, vehicle: Vehicle):
        if vehicle.stop_id == self.stop.id:
            # Okay so it's at least headed to the next stop, but is it within the bounding box?
            if self.bounding.contains(vehicle.latitude, vehicle.longitude):
                return True
        return False

class Light:
    def __init__(self, status: LightStatus):
        self.status = status

class StripConfig:
    def __init__(self, stops: list[LightStop]) -> None:
        self.stops = stops
        self.stops_by_light_id = {}
        self.stops_by_stop_id = {}
        for stop in stops:
            self.stops_by_light_id[stop.light_index] = stop
            self.stops_by_stop_id[stop.stop.id] = stop

    def find_last_stop(self, current_stop: LightStop) -> LightStop:
        current_index = len(self.stops) - 1
        while self.stops[current_index].stop.id != current_stop.stop.id and current_index >= 0:
            current_index -= 1
        return self.stops[current_index - 1]

    def calculate_strip(self, vehicles: list[Vehicle]):
        status = []
        counter = 0
        while (counter < self.stops[-1].light_index):
            stop_light = self.stops_by_light_id.get(counter)
            counter += 1
            if stop_light is None:
                status.append(Light(LightStatus.EMPTY))
            else:
                status.append(Light(LightStatus.STATION))

        for vehicle in vehicles:
            stop: LightStop = self.stops_by_stop_id.get(vehicle.stop_id)
            if (stop is None):
                # This can happen because the stop is out of range of our strip
                continue
            if (stop.is_vehicle_in_stop(vehicle)):
                status[stop.light_index] = Light(LightStatus.OCCUPIED)
            else:
                last_stop = self.find_last_stop(stop)
                intermediary_stops = stop.light_index - last_stop.light_index - 1
                percentage_trip = self.calculate_percentage(last_stop.bounding, stop.bounding, (vehicle.latitude, vehicle.longitude))
                current_intermediary = round(percentage_trip * intermediary_stops)
                # So last stop + current_intermediary is occupied
                status[last_stop.light_index + current_intermediary] = Light(LightStatus.OCCUPIED)

        return status



