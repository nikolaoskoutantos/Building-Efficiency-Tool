"""
Weather service for fetching weather data from external APIs.
"""


import requests
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from models.sensordata import WeatherData

class WeatherService:
    def __init__(self):
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))
        self.mode = os.getenv('MODE', 'Web2')
        self.base_url = os.getenv('WEATHER_BASE_URL', 'https://api.openweathermap.org/data/2.5/weather')
        self.api_key = os.getenv('WEATHER_API_KEY')
        self.bearer_token = os.getenv('WEATHER_BEARER_TOKEN')
        self.units = os.getenv('WEATHER_UNITS', 'metric')
        self.ipfs_gateway = os.getenv('IPFS_GATEWAY', 'https://ipfs.io/ipfs/')

    def fetch_weather(self, lat: float, lon: float, cid: str = None):
        if self.mode == 'Web2':
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": self.units
            }
            headers = {}
            if self.bearer_token:
                headers["Authorization"] = f"Bearer {self.bearer_token}"
            response = requests.get(self.base_url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        elif self.mode == 'Web3' and cid:
            # Fetch from IPFS using CID
            url = f"{self.ipfs_gateway}{cid}"
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        else:
            raise ValueError("Invalid mode or missing CID for Web3 weather fetch.")

    def fetch_weather(self, lat: float, lon: float):
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": self.units
        }
        headers = {}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        response = requests.get(self.base_url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()

    def store_weather(self, db: Session, lat: float, lon: float, weather_json: dict):
        wd = WeatherData(
            lat=lat,
            lon=lon,
            temperature=weather_json.get("main", {}).get("temp"),
            humidity=weather_json.get("main", {}).get("humidity"),
            pressure=weather_json.get("main", {}).get("pressure"),
            wind_speed=weather_json.get("wind", {}).get("speed"),
            wind_direction=weather_json.get("wind", {}).get("deg"),
            precipitation=weather_json.get("rain", {}).get("1h", 0),
            weather_description=weather_json.get("weather", [{}])[0].get("description")
        )
        db.add(wd)
        db.commit()
        print(f"✅ Stored weather data for ({lat}, {lon})")
