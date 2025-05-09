import requests
import psycopg2
import json
from datetime import datetime
import time

# --- Configuration ---
OPENWEATHER_API_KEY = "c4af157e9bcb318f3f4e49eec7eeb130"
CITY_LIST_FILE = "city.list.json"  # Download from OpenWeatherMap
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "user": "postgres",
    "password": "u",
    "dbname": "poc"
}

# --- Functions ---

def load_cities(limit=50):
    try:
        with open(CITY_LIST_FILE, "r", encoding="utf-8") as f:
            cities = json.load(f)
        return cities[:limit]  # Limit to 50 for testing
    except FileNotFoundError:
        print(f"❌ Error: The file {CITY_LIST_FILE} was not found.")
        raise
    except json.JSONDecodeError:
        print(f"❌ Error: Failed to parse {CITY_LIST_FILE}.")
        raise
    except Exception as e:
        print(f"❌ Error loading cities: {e}")
        raise

def fetch_bulk_weather(city_ids):
    try:
        ids = ",".join(str(cid) for cid in city_ids)
        url = f"https://api.openweathermap.org/data/2.5/group?id={ids}&units=metric&appid={OPENWEATHER_API_KEY}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get("list", [])
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error while fetching weather data: {e}")
        raise
    except requests.exceptions.RequestException as e:
        print(f"❌ Error making request to OpenWeather API: {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error fetching weather data: {e}")
        raise

def fetch_air_quality(lat, lon):
    try:
        url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data["list"][0]["main"]["aqi"] if data.get("list") else None
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error while fetching air quality data: {e}")
        raise
    except requests.exceptions.RequestException as e:
        print(f"❌ Error making request to OpenWeather API for air quality: {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error fetching air quality data: {e}")
        raise

def transform_weather(data, aqi):
    try:
        return {
            "timestamp": datetime.utcfromtimestamp(data["dt"]),
            "temperature": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "wind_speed": data["wind"]["speed"],
            "description": data["weather"][0]["description"] if data.get("weather") else None,
            "air_quality_index": aqi
        }
    except KeyError as e:
        print(f"❌ Missing expected key in weather data: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error while transforming weather data: {e}")
        return None

def is_valid_weather(data):
    if not data:
        print("❌ No data to validate.")
        return False
    return all(data.get(k) is not None for k in ["temperature", "humidity", "pressure"])

def insert_into_db(data, city, state):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        insert_query = """
            INSERT INTO weather_data (
                city, state, temperature, humidity, weather_description, air_quality_index, recorded_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(insert_query, (
            city,
            state,
            data["temperature"],
            data["humidity"],
            data["description"],
            data["air_quality_index"],
            data["timestamp"]
        ))

        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ Inserted data for {city}")
    except psycopg2.Error as e:
        print(f"❌ Database error while inserting data for {city}: {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error inserting data for {city}: {e}")
        raise

# --- Main Execution ---

if __name__ == "__main__":
    try:
        all_cities = load_cities(limit=50)  # Adjust limit for larger runs
        batch_size = 20
        for i in range(0, len(all_cities), batch_size):
            batch = all_cities[i:i + batch_size]
            city_ids = [city["id"] for city in batch]
            weather_data = fetch_bulk_weather(city_ids)

            for data in weather_data:
                city_name = data["name"]
                state = data.get("state", "NA")
                lat = data["coord"]["lat"]
                lon = data["coord"]["lon"]

                try:
                    aqi = fetch_air_quality(lat, lon)
                    transformed = transform_weather(data, aqi)

                    if is_valid_weather(transformed):
                        insert_into_db(transformed, city_name, state)
                    else:
                        print(f"⚠️ Invalid weather data for {city_name}")
                except Exception as e:
                    print(f"❌ Error processing {city_name}: {e}")

                time.sleep(1)  # To respect API rate limits

    except Exception as e:
        print(f"❌ General Error: {e}")
