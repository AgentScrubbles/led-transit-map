from google.transit import gtfs_realtime_pb2
import requests
from protobuf_to_dict import protobuf_to_dict




class TransitFeed:

    def GetFeed(self):
        feed = gtfs_realtime_pb2.FeedMessage()
        response = requests.get(
                'http://api.pugetsound.onebusaway.org/api/gtfs_realtime/vehicle-positions-for-agency/40.pb', allow_redirects=True)
        feed.ParseFromString(response.content)

        zet_dict = protobuf_to_dict(feed)

        return zet_dict
