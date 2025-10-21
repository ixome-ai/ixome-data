import json
import os
import logging
import uuid
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
import psycopg2
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(dotenv_path='/home/vincent/ixome/.env', override=True)

def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("PG_DBNAME"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        host=os.getenv("PG_HOST", "localhost"),
        port=os.getenv("PG_PORT", 5432)
    )

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index_name = "troubleshooter-index"
if index_name not in pc.list_indexes().names():
    pc.create_index(name=index_name, dimension=1536, metric='cosine', spec=ServerlessSpec(cloud='aws', region=os.getenv("PINECONE_ENVIRONMENT", "us-east-1")))
index = pc.Index(index_name)

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_embedding(text):
    if not text.strip():
        return None
    try:
        response = openai_client.embeddings.create(input=text, model="text-embedding-ada-002")
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return None

def load_json_data(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                if isinstance(data, dict):
                    data = [data]
                return [item for item in data if isinstance(item, dict) and ('issue' in item or 'title' in item) and ('solution' in item or 'description' in item)]
            except json.JSONDecodeError:
                f.seek(0)
                data = []
                for line in f:
                    if line.strip():
                        try:
                            item = json.loads(line)
                            if isinstance(item, dict) and ('issue' in item or 'title' in item) and ('solution' in item or 'description' in item):
                                # Normalize keys
                                if 'title' in item:
                                    item['issue'] = item['title']
                                if 'description' in item:
                                    item['solution'] = item['description']
                                data.append(item)
                        except json.JSONDecodeError:
                            continue
                return data
    except Exception as e:
        logger.error(f"Load {file_path} failed: {e}")
        return []

def insert_into_postgres(data):
    db_ids = []
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for item in data:
                    cur.execute(
                        "INSERT INTO dealer_info (brand, issue, solution, product, category, url) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                        ('Lutron', item.get('issue', ''), item.get('solution', ''), item.get('product', ''), item.get('category', ''), item.get('url', ''))
                    )
                    db_id = cur.fetchone()[0]
                    db_ids.append(db_id)
                conn.commit()
                logger.info(f"Inserted {len(data)} to PG")
    except Exception as e:
        logger.error(f"PG insert failed: {e}")
    return db_ids

def upsert_to_pinecone(data, db_ids):
    vectors = []
    for item, db_id in zip(data, db_ids):
        solution = item.get('solution', '')
        text = f"Lutron {item.get('issue', '')} {solution} {item.get('product', '')}".strip()
        embedding = get_embedding(text)
        if embedding is None:
            continue
        word_count = len(solution.split())
        metadata = {
            'brand': 'Lutron',
            'issue': item.get('issue', ''),
            'solution': solution if word_count < 100 else '',
            'product': item.get('product', ''),
            'category': item.get('category', ''),
            'url': item.get('url', ''),
            'db_id': str(db_id)
        }
        vectors.append({'id': str(uuid.uuid4()), 'values': embedding, 'metadata': metadata})
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        index.upsert(vectors=vectors[i:i + batch_size])
        logger.info(f"Upsert batch {i//batch_size + 1}")
    logger.info(f"Total {len(vectors)} to Pinecone")

def main():
    data_files = [
        '/home/vincent/ixome/ixome-data/scrapers/control4_scraper/control4_data.json',
        '/home/vincent/ixome/ixome-data/scrapers/lutron_scraper/lutron_data_batch1.json',
        '/home/vincent/ixome/ixome-data/scrapers/lutron_scraper/lutron_data.json',
        '/home/vincent/ixome/ixome-data/scrapers/lutron_scraper/lutron_homeworks_data.json'  # New
    ]
    all_data = []
    for file_path in data_files:
        if os.path.exists(file_path):
            all_data.extend(load_json_data(file_path))
    if all_data:
        db_ids = insert_into_postgres(all_data)
        if len(db_ids) == len(all_data):
            upsert_to_pinecone(all_data, db_ids)
    else:
        logger.warning("No data")

if __name__ == "__main__":
    main()