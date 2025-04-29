import psycopg2
from .embedder import get_weather_and_embedding
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)

def store_weather_data_and_embedding(city: str):
    """Store both structured data and vector embedding for a city."""
    try:
        # Fetch weather data and embedding
        weather, description_text, embedding = get_weather_and_embedding(city)
    except Exception as e:
        logging.error(f"❌ Error getting weather and embedding for {city}: {e}")
        return  # Exit early if data retrieval fails

    try:
        # Establish database connection
        conn = psycopg2.connect(
            dbname="poc",
            user="postgres",
            password="u",
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()

        try:
            # Insert structured weather data into weather_structured table
            cur.execute("""
                INSERT INTO weather_structured (
                    city, type, timestamp, temperature, humidity,
                    pressure, wind_speed, description
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                weather["city"], weather["type"], weather["timestamp"],
                weather["temperature"], weather["humidity"],
                weather["pressure"], weather["wind_speed"], weather["description"]
            ))

            # Insert the vector embedding into weather_embeddings table
            cur.execute("""
                INSERT INTO weather_embeddings (location, description, embedding)
                VALUES (%s, %s, %s::vector)
            """, (weather["city"], description_text, embedding))

            conn.commit()  # Commit the transaction
            logging.info(f"[✓] Stored weather and embedding for: {city}")

        except psycopg2.Error as e:
            # Handle database errors (e.g., query issues)
            conn.rollback()  # Rollback the transaction on error
            logging.error(f"❌ SQL Error while inserting data for {city}: {e}")
            raise  # Re-raise the error to be handled by outer block

        finally:
            # Ensure the cursor and connection are closed after operations
            cur.close()
            conn.close()

    except psycopg2.OperationalError as e:
        logging.error(f"❌ Database connection error for {city}: {e}")
    except psycopg2.InterfaceError as e:
        logging.error(f"❌ Database interface error for {city}: {e}")
    except Exception as e:
        logging.error(f"❌ Unexpected error while storing data for {city}: {e}")
