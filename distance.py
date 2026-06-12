
import os
import time
import openrouteservice
import googlemaps
import pandas as pd
from settings import Settings, OUTPUT_FILE, INPUT_FILE, INPUT_FILE_CSV

settings = Settings()

# Terminal full names for geocoding
TERMINAL_MAP = {
    "ENG": "Enugu, Nigeria",
    "KAN": "Kano, Nigeria",
    "PHC": "Port Harcourt, Nigeria",
    "SAP": "Sapele, Nigeria",
    "GGLD": "Gwagwalada, Nigeria",
}

# Terminal site prefixes to strip from route names before extracting destination
SITE_PREFIXES = [
    "ENUGU SITE",
    "PORT-HARCOURT SITE",
    "SAPELE SITE",
    "KANO SITE",
    "GWAGWALADA SITE",
    "GWAGWALADA-SITE",
]

# client = openrouteservice.Client(key=settings.api_key)
gmaps = googlemaps.Client(key=settings.api_key)

# Mini cache
geocode_cache = {}


def geocode(place_name):
    """Convert a place name to (lng, lat) coordinates"""
    if place_name in geocode_cache:
        return geocode_cache[place_name]
    
    try:
        result = gmaps.geocode(place_name)
        if result:
            location = result[0]['geometry']['location']
            coords = (location["lng"], location["lat"])
            geocode_cache[place_name] = coords
            return coords
        
        print(f"Geocoding failed for {place_name}: No results found.")
        geocode_cache[place_name] = (None, None)
        return None, None
    except Exception as e:
        print(f"Geocoding error for {place_name}: {e}")
        geocode_cache[place_name] = (None, None)
        return None, None

def calculate_road_distance(origin_coords, destination_coords):
    """Calculate road distance in KM between two coordinates"""
    try:
        # route = client.directions(coordinates=[origin_coords, destination_coords], 
        #                         profile='driving-hgv', format='geojson')
        origin = (origin_coords[1], origin_coords[0])
        destination = (destination_coords[1], destination_coords[0])
        result = gmaps.distance_matrix(
            origins=[origin],
            destinations=[destination],
            mode="driving",
            units="metric"
        )
        # distance_in_meters = route['features'][0]['properties']['summary']['distance']
        element = result["rows"][0]["elements"][0]
        if element["status"] != "OK":
            print(f"  Routing status: {element['status']}")
            return None
        distance_in_meters = element["distance"]["value"]
        estimated_distance = round(distance_in_meters / 1000, 2)  # Convert to kilometers
        print(f"Calculated distance between {origin_coords} and {destination_coords}: {estimated_distance} km")
        return estimated_distance 
    except Exception as e:
        print(f"Routing error between {origin_coords} and {destination_coords}: {e}")
    return None

def extract_destination(route_name):
    """Pull the destination city out of the route name string."""
    cleaned = route_name.split("__")[0].strip() # removing suffixes like __RENAMED__1

    # Strip known site prefixes to get to the city name
    upper = cleaned.upper()
    for prefix in SITE_PREFIXES:
        if upper.startswith(prefix):
            remainder = cleaned[len(prefix):].lstrip(" -").strip()
            return remainder + ", Nigeria"
    
    if " - " in cleaned:
        parts = cleaned.split(" - ", 1)
        return parts[1].strip() + ", Nigeria"

    # Take everything after the first dash
    parts = cleaned.split("-", 1)
    if len(parts) > 1:
        return parts[1].strip() + ", Nigeria"
    return cleaned + ", Nigeria"


# -------- MAIN FUNCTION -----------------
df = pd.read_excel(INPUT_FILE)

if os.path.exists(OUTPUT_FILE):
        df = pd.read_excel(OUTPUT_FILE)  # resume from saved progress
else:
        df = pd.read_excel(INPUT_FILE) 

for index, row in df.iterrows():
    if pd.notna(row["Distance"]) and row["Distance"] != 0.0:
        print(f"Row {index}: Already has distance — skipping")
        continue
    
    terminal_code = str(row["Terminal"]).strip()
    route_name = str(row["Name"]).strip()

    origin_label = TERMINAL_MAP.get(terminal_code, None)
    destination_label = extract_destination(route_name)

    if not origin_label:
        print(f"Unknown terminal code '{terminal_code}' at row {index}. Skipping.")
        df.at[index, "Distance"] = None
        continue
    
    if not destination_label:
        print(f"  Skipping: could not parse destination from '{route_name}'")
        df.at[index, "Distance"] = None
        continue

    print(f"Processing row {index}: Terminal '{terminal_code}' -> '{origin_label}', Route '{route_name}' -> '{destination_label}'")

    try:
        print(f"Row {index}: Geocoding origin: {origin_label} -> {destination_label}")
        origin_coords = geocode(origin_label)
        dest_coords = geocode(destination_label)

        if None in origin_coords or None in dest_coords:
            print(f"  Skipping: geocoding failed")
            df.at[index, "Distance"] = None
            continue

        distance = calculate_road_distance(origin_coords, dest_coords)
        df.at[index, "Distance"] = distance
        print(f"Row {index}: Distance calculated: {distance} km")

        time.sleep(1.5)
    except Exception as e:
        print(f" x Failed: {e}")
        df.at[index, "Distance"] = None
        continue

df.to_excel(OUTPUT_FILE, index=False)
print(f"\nDone!! Output saved to {OUTPUT_FILE}")
print(f"\n Cache: {geocode_cache}")