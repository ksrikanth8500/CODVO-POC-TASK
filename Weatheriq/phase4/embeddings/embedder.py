import requests
from sentence_transformers import SentenceTransformer, LoggingHandler
from datetime import datetime
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO, handlers=[LoggingHandler()])

# Hardcoded API key
OPENWEATHER_API_KEY = "c4af157e9bcb318f3f4e49eec7eeb130"

# Initialize the model for embeddings
try:
    model = SentenceTransformer("all-MiniLM-L6-v2")
    logging.info("SentenceTransformer model loaded successfully.")
except Exception as e:
    logging.error(f"❌ Failed to load SentenceTransformer model: {e}")
    raise  # Re-raise exception after logging

def fetch_weather(city: str):
    """Fetch current weather from OpenWeatherMap for a given city."""
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
        response = requests.get(url)

        if response.status_code != 200:
            raise Exception(f"Weather fetch failed for {city}: {response.status_code} - {response.text}")

        data = response.json()

        # Check if 'weather' and 'main' fields are in the response to avoid KeyError
        if 'weather' not in data or 'main' not in data:
            raise KeyError(f"Missing expected keys in response for {city}: 'weather' or 'main'")

        weather_info = {
            "city": city,
            "type": data['weather'][0]['main'],
            "timestamp": datetime.utcfromtimestamp(data['dt']),
            "temperature": data['main']['temp'],
            "humidity": data['main']['humidity'],
            "pressure": data['main']['pressure'],
            "wind_speed": data['wind']['speed'],
            "description": data['weather'][0]['description'],
        }

        # Text for embedding
        text = (
            f"Weather in {city}: {weather_info['description']}. "
            f"Temperature: {weather_info['temperature']}°C. "
            f"Humidity: {weather_info['humidity']}%. "
            f"Pressure: {weather_info['pressure']} hPa. "
            f"Wind Speed: {weather_info['wind_speed']} m/s."
        )

        return weather_info, text

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Request error while fetching weather for {city}: {e}")
        raise  # Re-raise exception after logging

    except KeyError as e:
        logging.error(f"❌ Missing key in weather data for {city}: {e}")
        raise
