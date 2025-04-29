import sys
import os
import logging
import traceback
import numpy as np
import psycopg2

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from fastapi import FastAPI, Query
from sentence_transformers import SentenceTransformer
from phase4.embeddings.storage import store_weather_data_and_embedding

# Setup logging
logging.basicConfig(level=logging.INFO)

# FastAPI app initialization
app = FastAPI()
model = SentenceTransformer("all-MiniLM-L6-v2")

def query_embedding(text: str):
    try:
        emb = model.encode(text)
        # Ensure the embedding is a list (convert from numpy array if necessary)
        if isinstance(emb, np.ndarray):
            emb = emb.tolist()  # Convert numpy array to list
        elif isinstance(emb, list) and isinstance(emb[0], list):  # batch case
            emb = emb[0]
        return emb
    except Exception as e:
        logging.error(f"❌ Error generating embedding for text: {text} - {e}")
        raise

@app.get("/query/")
def search_weather_info(query: str = Query(...)):
    try:
        # Try to fetch & store if not already in DB
        store_weather_data_and_embedding(query)
    except Exception as e:
        logging.info(f"[INFO] Weather data might already exist, continuing search. Error: {e}")

    try:
        # Generate query embedding
        query_emb = query_embedding(query)

        # Connect to the PostgreSQL database
        try:
            conn = psycopg2.connect(
                dbname="poc",
                user="postgres",
                password="u",
                host="localhost",
                port="5432"
            )
            cur = conn.cursor()
        except psycopg2.OperationalError as e:
            logging.error(f"❌ Database connection error: {e}")
            return {"error": "Failed to connect to the database."}

        try:
            # Execute the vector similarity query
            cur.execute("""
                SELECT location, description, embedding <-> %s::vector AS distance
                FROM weather_embeddings
                ORDER BY distance ASC
                LIMIT 3;
            """, (query_emb,))

            results = cur.fetchall()
            cur.close()
            conn.close()

            if not results:
                return {"message": "No similar weather data found."}

            return {
                "matches": [
                    {
                        "location": r[0],
                        "description": r[1],
                        "similarity_score": r[2]
                    } for r in results
                ]
            }

        except psycopg2.Error as e:
            logging.error(f"❌ SQL Error while querying database: {e}")
            conn.rollback()
            return {"error": "Failed to execute query."}

        except Exception as e:
            logging.error(f"❌ Unexpected error during query execution: {e}")
            return {"error": "An unexpected error occurred during the query execution."}

    except Exception as e:
        logging.error(f"[ERROR] Vector search failed: {str(e)}")
        traceback.print_exc()
        return {"error": "Failed to process vector search."}
