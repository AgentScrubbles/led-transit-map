from transit import Stop

class BoundingArea:
    def __init__(self, x1: float, y1: float, x2: float, y2: float):
        self.X1 = x1
        self.Y1 = y1
        self.X2 = x2
        self.Y2 = y2

    @staticmethod
    def FromPoint(x: float, y: float, offset: float):
        from_center_offset = offset / 2
        x1 = x - from_center_offset
        y1 = y - from_center_offset
        x2 = x + from_center_offset
        y2 = y + from_center_offset
        return BoundingArea(x1, y1, x2, y2)


class Light:
    def __init__(self, index: int):
        self.index = index
        self.prev_stop: Light = None
        self.next_stop: Light = None

    def prev(self):
        return self.prev_stop
    
    def next(self):
        return self.next_stop
    
    def setBoundingArea(self, bounding: BoundingArea):
        self.bounding = bounding

    def setNextStop(self, next_stop: Stop):
        self.next_stop = next_stop

class AreaLight(Light):
    def __init__(self, index: int, prev_stop: Stop):
        Light.__init__(self, index)
        self.prev_stop = prev_stop

class StopLight(Light):
    def __init__(self, index: int, stop: Stop):
        Light.__init__(self, index)
        self.index = index
        self.stop = stop
        self.bounding = BoundingArea.FromPoint(stop.latitude, stop.longitude, 0.1)

    def SetNextStop(self, stop: Stop):
        self.next_stop = stop


class StripConfig:
    def __init__(self, stops: list[Stop]) -> None:
        self.stops = stops

    def fill_strip(self):

        strip_length = len(self.stops)
        self.strip: list[Light] = []
        last_stop: StopLight = None
        for index in range(strip_length):
            item = self.stops[index]
            if (item is Stop):
                self.strip[index] = StopLight(index, item)
                if last_stop is not None:
                    last_stop.SetNextStop(item)
                last_stop = item
            if (item is None):
                self.strip[index] = AreaLight(index, last_stop)

        # Here we have a list of stops and areas, but they're not hooked up
        for index, item in enumerate(self.strip):
            # Last stops are already defined, but we need to get next stops
            counter = index
            while(counter < len(self.strip) and self.strip[counter] is not StopLight):
                counter += 1
            if counter is not None:
                item.setNextStop(self.strip[counter])

        # Here we have each stop wired with it's next stops, we can now fill in
        # the bounding boxes of each
