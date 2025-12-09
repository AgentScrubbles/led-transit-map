#!/usr/bin/env python3
"""
Utility to list stops for transit routes from OneBusAway API.
Displays stops in a side-by-side format showing both directions.

Usage:
    python list_stops.py                    # Lists available routes
    python list_stops.py <route_id>         # Shows stops for a specific route
    python list_stops.py 40_100479          # Example: 1 Line
"""

import os
import sys
from dotenv import load_dotenv
from onebusaway import OnebusawaySDK

load_dotenv()

client = OnebusawaySDK(
    api_key=os.getenv("ONEBUSAWAY_API_KEY")
)

# Route IDs we care about (from strips.json)
KNOWN_ROUTES = [
    "40_100479",  # 1 Line
    "40_2LINE",   # 2 Line
]


def get_route_info(route_id: str):
    """Fetch route details from API."""
    try:
        result = client.route.retrieve(route_id)
        return result.data.entry
    except Exception as e:
        print(f"Error fetching route {route_id}: {e}")
        return None


def get_stops_for_route(route_id: str):
    """
    Fetch all stops for a route, grouped by direction.
    Returns: dict with direction_id as key, list of stops as value
    """
    try:
        result = client.trips_for_route.list(
            route_id,
            include_schedule=True,
            include_status=True
        )

        # Build lookup of stops from references
        stops_lookup = {}
        if hasattr(result.data.references, 'stops'):
            for stop in result.data.references.stops:
                stops_lookup[stop.id] = stop

        # Build lookup of trips with their directions
        trips_lookup = {}
        if hasattr(result.data.references, 'trips'):
            for trip in result.data.references.trips:
                trips_lookup[trip.id] = trip

        # Group stops by direction
        # We'll use the first trip in each direction to get the ordered stop list
        stops_by_direction = {0: [], 1: []}
        seen_directions = {0: set(), 1: set()}

        for trip_status in result.data.list:
            trip_id = trip_status.trip_id
            trip = trips_lookup.get(trip_id)
            if not trip:
                continue

            direction = int(trip.direction_id)

            # Get stop times from schedule
            if hasattr(trip_status, 'schedule') and trip_status.schedule:
                stop_times = trip_status.schedule.stop_times
                for stop_time in stop_times:
                    stop_id = stop_time.stop_id
                    if stop_id not in seen_directions[direction]:
                        seen_directions[direction].add(stop_id)
                        stop = stops_lookup.get(stop_id)
                        if stop:
                            stops_by_direction[direction].append({
                                'id': stop.id,
                                'code': getattr(stop, 'code', stop.id),
                                'name': stop.name,
                                'lat': stop.lat,
                                'lon': stop.lon
                            })
                # Only need one complete trip per direction
                if len(stops_by_direction[direction]) > 0:
                    break

        # Get ordered stops for each direction by re-processing
        # Reset and get properly ordered
        stops_by_direction = {0: [], 1: []}
        processed_directions = set()

        for trip_status in result.data.list:
            trip_id = trip_status.trip_id
            trip = trips_lookup.get(trip_id)
            if not trip:
                continue

            direction = int(trip.direction_id)

            if direction in processed_directions:
                continue

            if hasattr(trip_status, 'schedule') and trip_status.schedule:
                stop_times = trip_status.schedule.stop_times
                for stop_time in stop_times:
                    stop_id = stop_time.stop_id
                    stop = stops_lookup.get(stop_id)
                    if stop:
                        stops_by_direction[direction].append({
                            'id': stop.id,
                            'code': getattr(stop, 'code', stop.id),
                            'name': stop.name,
                            'lat': stop.lat,
                            'lon': stop.lon
                        })
                processed_directions.add(direction)

            if len(processed_directions) == 2:
                break

        return stops_by_direction

    except Exception as e:
        print(f"Error fetching stops for route {route_id}: {e}")
        import traceback
        traceback.print_exc()
        return None


def match_stops_by_name(stops_dir_0, stops_dir_1):
    """
    Match stops between directions by name (normalized).
    Returns list of tuples: (dir_0_stop, dir_1_stop, name)
    Either stop can be None if only exists in one direction.
    """
    def normalize_name(name):
        # Normalize for matching - lowercase, remove common suffixes
        n = name.lower().strip()
        for suffix in [' station', ' transit center', ' tc']:
            if n.endswith(suffix):
                n = n[:-len(suffix)]
        return n

    # Build lookup by normalized name
    dir_0_by_name = {normalize_name(s['name']): s for s in stops_dir_0}
    dir_1_by_name = {normalize_name(s['name']): s for s in stops_dir_1}

    all_names = set(dir_0_by_name.keys()) | set(dir_1_by_name.keys())

    # Use direction 0 order as base, then add any extras from direction 1
    result = []
    seen_names = set()

    for stop in stops_dir_0:
        norm_name = normalize_name(stop['name'])
        seen_names.add(norm_name)
        dir_1_stop = dir_1_by_name.get(norm_name)
        result.append((stop, dir_1_stop, stop['name']))

    # Add any stops only in direction 1
    for stop in stops_dir_1:
        norm_name = normalize_name(stop['name'])
        if norm_name not in seen_names:
            result.append((None, stop, stop['name']))

    return result


def print_stops_table(route_id: str, route_name: str, stops_by_direction: dict):
    """Print stops in a formatted table."""
    stops_0 = stops_by_direction.get(0, [])
    stops_1 = stops_by_direction.get(1, [])

    if not stops_0 and not stops_1:
        print("No stops found for this route.")
        return

    # Determine direction labels based on route
    # Direction 0 is typically Southbound/Westbound, Direction 1 is Northbound/Eastbound
    # But this varies - we'll use the first/last stop names to guess
    dir_0_label = "Direction 0"
    dir_1_label = "Direction 1"

    if stops_0:
        first_0 = stops_0[0]['name'] if stops_0 else ''
        last_0 = stops_0[-1]['name'] if stops_0 else ''
        dir_0_label = f"To {last_0}"
    if stops_1:
        first_1 = stops_1[0]['name'] if stops_1 else ''
        last_1 = stops_1[-1]['name'] if stops_1 else ''
        dir_1_label = f"To {last_1}"

    print(f"\n{'='*80}")
    print(f"Route: {route_id} - {route_name}")
    print(f"{'='*80}")
    print(f"\nDirection 0: {dir_0_label} ({len(stops_0)} stops)")
    print(f"Direction 1: {dir_1_label} ({len(stops_1)} stops)")
    print()

    # Print header
    header = f"{'Dir 0 Code':<15} | {'Station Name':<35} | {'Dir 1 Code':<15}"
    print(header)
    print("-" * len(header))

    # Match and print stops
    matched = match_stops_by_name(stops_0, stops_1)

    for dir_0_stop, dir_1_stop, name in matched:
        code_0 = dir_0_stop['code'] if dir_0_stop else '-'
        code_1 = dir_1_stop['code'] if dir_1_stop else '-'
        print(f"{code_0:<15} | {name:<35} | {code_1:<15}")

    print()

    # Also print full list for each direction separately
    print(f"\n--- Direction 0 Stops (in order) ---")
    print(f"{'#':<4} {'Code':<15} {'Name':<40} {'Lat':<12} {'Lon':<12}")
    print("-" * 85)
    for i, stop in enumerate(stops_0, 1):
        print(f"{i:<4} {stop['code']:<15} {stop['name']:<40} {stop['lat']:<12.6f} {stop['lon']:<12.6f}")

    print(f"\n--- Direction 1 Stops (in order) ---")
    print(f"{'#':<4} {'Code':<15} {'Name':<40} {'Lat':<12} {'Lon':<12}")
    print("-" * 85)
    for i, stop in enumerate(stops_1, 1):
        print(f"{i:<4} {stop['code']:<15} {stop['name']:<40} {stop['lat']:<12.6f} {stop['lon']:<12.6f}")


def list_known_routes():
    """List the known routes from config."""
    print("\nKnown Routes:")
    print("-" * 50)
    for route_id in KNOWN_ROUTES:
        route = get_route_info(route_id)
        if route:
            name = getattr(route, 'long_name', '') or getattr(route, 'short_name', route_id)
            print(f"  {route_id:<20} {name}")
        else:
            print(f"  {route_id:<20} (unable to fetch)")
    print()
    print("Usage: python list_stops.py <route_id>")
    print("Example: python list_stops.py 40_100479")


def main():
    if len(sys.argv) < 2:
        list_known_routes()
        return

    route_id = sys.argv[1]

    # Get route info
    route = get_route_info(route_id)
    if not route:
        print(f"Could not find route: {route_id}")
        return

    route_name = getattr(route, 'long_name', '') or getattr(route, 'short_name', route_id)

    # Get stops
    print(f"Fetching stops for {route_id}...")
    stops_by_direction = get_stops_for_route(route_id)

    if stops_by_direction:
        print_stops_table(route_id, route_name, stops_by_direction)


if __name__ == "__main__":
    main()
