import json
import os
import logging
import uuid
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
import psycopg2
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(dotenv_path='/home/vincent/ixome/.env', override=True)

# PostgreSQL connection
def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("PG_DBNAME"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT")
    )

# Pinecone setup
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index_name = "troubleshooter-index"
if index_name not in pc.list_indexes().names():
    logger.info(f"Creating new index {index_name} with dimension 1536.")
    pc.create_index(
        name=index_name,
        dimension=1536,
        metric='cosine',
        spec=ServerlessSpec(cloud='aws', region=os.getenv("PINECONE_ENVIRONMENT", "us-east-1"))
    )
else:
    index_desc = pc.describe_index(index_name)
    if index_desc.dimension != 1536:
        logger.info(f"Index {index_name} has dimension {index_desc.dimension}. Deleting and recreating with 1536.")
        pc.delete_index(index_name)
        pc.create_index(
            name=index_name,
            dimension=1536,
            metric='cosine',
            spec=ServerlessSpec(cloud='aws', region=os.getenv("PINECONE_ENVIRONMENT", "us-east-1"))
        )
index = pc.Index(index_name)

# OpenAI client for embeddings
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_embedding(text):
    """Generate embedding for the given text using OpenAI."""
    if not text.strip():
        logger.warning("Empty text provided for embedding. Skipping.")
        return None
    try:
        response = openai_client.embeddings.create(
            input=text,
            model="text-embedding-ada-002"
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None

def load_json_data(file_path):
    """Load JSON data, handling both array and line-by-line formats."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                # Try loading as a single JSON array
                data = json.load(f)
                if isinstance(data, dict):
                    data = [data]
                return [item for item in data if isinstance(item, dict) and 'issue' in item and 'solution' in item]
            except json.JSONDecodeError:
                # Fallback to line-by-line JSON
                f.seek(0)
                data = []
                for line in f:
                    if line.strip():
                        try:
                            item = json.loads(line)
                            if isinstance(item, dict) and 'issue' in item and 'solution' in item:
                                data.append(item)
                        except json.JSONDecodeError as e:
                            logger.error(f"Skipping malformed JSON line in {file_path}: {line[:50]}... {e}")
                            continue
                return data
    except Exception as e:
        logger.error(f"Failed to load {file_path}: {e}")
        return []

def insert_into_postgres(data):
    """Insert data into PostgreSQL dealer_info table, returning IDs."""
    db_ids = []
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for item in data:
                    cur.execute(
                        "INSERT INTO dealer_info (brand, issue, solution) VALUES (%s, %s, %s) RETURNING id",
                        (item.get('brand', 'Unknown'), item.get('issue', 'Unknown'), item.get('solution', 'No solution'))
                    )
                    db_id = cur.fetchone()[0]
                    db_ids.append(db_id)
                conn.commit()
                logger.info(f"Inserted {len(data)} records into PostgreSQL")
    except Exception as e:
        logger.error(f"PostgreSQL insert failed: {e}")
    return db_ids

def upsert_to_pinecone(data, db_ids):
    """Upsert short answers to Pinecone, with db_id for long answers."""
    try:
        vectors = []
        for item, db_id in zip(data, db_ids):
            solution = item.get('solution', '')
            word_count = len(solution.split())
            is_short = word_count < 100  # Short answer threshold
            text = f"{item.get('brand', '')} {item.get('issue', '')} {solution} {item.get('product', '')}".strip()
            embedding = get_embedding(text)
            if embedding is None:
                continue
            vector_id = str(uuid.uuid4())
            metadata = {
                'brand': item.get('brand', 'Unknown'),
                'issue': item.get('issue', 'Unknown'),
                'solution': solution if is_short else '',
                'product': item.get('product', ''),
                'category': item.get('category', ''),
                'url': item.get('url', ''),
                'db_id': str(db_id)  # Pointer to PostgreSQL
            }
            vectors.append({
                'id': vector_id,
                'values': embedding,
                'metadata': metadata
            })
        # Batch upsert (100 vectors at a time)
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            index.upsert(vectors=batch)
            logger.info(f"Upserted {len(batch)} vectors to Pinecone (batch {i//batch_size + 1})")
        if vectors:
            logger.info(f"Total upserted {len(vectors)} vectors to Pinecone")
        else:
            logger.warning("No vectors generated to upsert.")
    except Exception as e:
        logger.error(f"Pinecone upsert failed: {e}")

def main():
    """Load scraped data into PostgreSQL and Pinecone."""
    data_files = [
        '/home/vincent/ixome/ixome-data/scrapers/control4_scraper/control4_data.json',
        '/home/vincent/ixome/ixome-data/scrapers/lutron_scraper/lutron_data_batch1.json',
        '/home/vincent/ixome/ixome-data/scrapers/lutron_scraper/lutron_data.json'
    ]
    all_data = []
    for file_path in data_files:
        data = load_json_data(file_path)
        all_data.extend(data)
    
    if all_data:
        db_ids = insert_into_postgres(all_data)
        if len(db_ids) == len(all_data):
            upsert_to_pinecone(all_data, db_ids)
        else:
            logger.error("Mismatch between data and DB IDs; skipping Pinecone upsert")
    else:
        logger.warning("No data loaded from files")

if __name__ == "__main__":
    main()