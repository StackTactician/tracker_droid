"""Location tracking utilities"""
import logging
import requests
import geocoder

try:
    from config import OPENCAGE_API_KEY, LOCATIONIQ_API_KEY
except ImportError:
    OPENCAGE_API_KEY = ""
    LOCATIONIQ_API_KEY = ""


def get_location_data():
    """Get device location via IP geolocation."""
    location_info = {
        'latitude': None,
        'longitude': None,
        'address': None,
        'ip_address': None,
        'method': None
    }
    try:
        g = geocoder.ip('me')
        if g.ok:
            location_info['latitude'] = g.lat
            location_info['longitude'] = g.lng
            location_info['address'] = g.address
            location_info['ip_address'] = g.ip
            location_info['method'] = 'IP Geolocation'
            if location_info['latitude'] and location_info['longitude']:
                better_address = get_address_from_coords(
                    location_info['latitude'],
                    location_info['longitude']
                )
                if better_address and better_address != "Address not available":
                    location_info['address'] = better_address
            return location_info
    except Exception as e:
        logging.error(f"IP geolocation failed: {e}")
    return location_info


def get_address_from_coords(lat, lng):
    """Reverse geocode coordinates to address."""
    session = requests.Session()
    session.headers.update({'User-Agent': 'Boyscout/1.0'})
    
    if OPENCAGE_API_KEY and not OPENCAGE_API_KEY.startswith("YOUR_"):
        try:
            url = f"https://api.opencagedata.com/geocode/v1/json?q={lat}+{lng}&key={OPENCAGE_API_KEY}"
            response = session.get(url, timeout=5)
            if response.status_code == 200:
                results = response.json().get('results', [])
                if results and results[0].get('formatted'):
                    return results[0]['formatted']
        except Exception as e:
            logging.error(f"OpenCage geocoding failed: {e}")
    
    if LOCATIONIQ_API_KEY and not LOCATIONIQ_API_KEY.startswith("YOUR_"):
        try:
            url = f"https://us1.locationiq.com/v1/reverse.php?key={LOCATIONIQ_API_KEY}&lat={lat}&lon={lng}&format=json"
            response = session.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('display_name'):
                    return data['display_name']
        except Exception as e:
            logging.error(f"LocationIQ geocoding failed: {e}")
    
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}"
        response = session.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('display_name'):
                return data['display_name']
    except Exception as e:
        logging.error(f"Nominatim geocoding failed: {e}")
    
    return "Address not available"
