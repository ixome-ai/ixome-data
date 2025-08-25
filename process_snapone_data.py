import json
import psycopg2
from pinecone import Pinecone, ServerlessSpec
import os
from dotenv import load_dotenv
import logging
import openai
import time

# Setup logging
logging.basicConfig(level=logging.INFO, filename='/home/vincent/ixome/data-1/data_processing.log',
                    format='%(asctime)s - %(levelname)s - %(message)s', filemode='w')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(dotenv_path='/home/vincent/ixome/.env')

def init_postgres():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('PG_DBNAME', 'ixome_db'),
            user=os.getenv('PG_USER', 'postgres'),
            password=os.getenv('PG_PASSWORD', 'HwCwTd2120#'),
            host=os.getenv('PG_HOST', 'localhost'),
            port=os.getenv('PG_PORT', '5432')
        )
        logger.info("Connected to PostgreSQL")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        raise

def init_pinecone():
    try:
        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        index_name = 'troubleshooter-index'
        if index_name not in pc.list_indexes().names():
            pc.create_index(
                name=index_name,
                dimension=1536,
                metric='cosine',
                spec=ServerlessSpec(cloud='aws', region=os.getenv('PINECONE_ENVIRONMENT', 'us-east-1'))
            )
            logger.info(f"Created Pinecone index: {index_name}")
        return pc.Index(index_name)
    except Exception as e:
        logger.error(f"Failed to initialize Pinecone: {e}")
        raise

def generate_embedding(text):
    try:
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.embeddings.create(
            input=text[:8192],
            model='text-embedding-ada-002'
        )
        logger.info(f"Generated embedding for text '{text[:50]}...'")
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Failed to generate embedding for text '{text[:50]}...': {e}")
        return None

def process_snapone_data(json_path='/home/vincent/ixome/scrapy-selenium/control4_scraper/control4_data.json'):
    # Load JSON data
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} records from {json_path}")
    except Exception as e:
        logger.error(f"Failed to load JSON: {e}")
        raise

    # Initialize PostgreSQL
    conn = init_postgres()
    cursor = conn.cursor()

    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS snapone_pdfs (
            id SERIAL PRIMARY KEY,
            url TEXT NOT NULL UNIQUE,
            product TEXT NOT NULL,
            category TEXT,
            issue TEXT,
            solution TEXT,
            depth INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    logger.info("Ensured snapone_pdfs table exists")

    # Insert data with deduplication
    inserted = 0
    seen_urls = set()
    for item in data:
        url = item.get('url', '')
        if url in seen_urls:
            logger.info(f"Skipping duplicate URL: {url}")
            continue
        seen_urls.add(url)
        try:
            cursor.execute("""
                INSERT INTO snapone_pdfs (url, product, category, issue, solution, depth)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO NOTHING;
            """, (
                url,
                item.get('product', 'Control4 Product'),
                item.get('category', 'PDF Document'),
                item.get('issue', 'unknown'),
                item.get('solution', ''),
                item.get('depth', 0)
            ))
            inserted += 1
        except Exception as e:
            logger.error(f"Failed to insert record {url}: {e}")
    conn.commit()
    logger.info(f"Inserted {inserted} records into PostgreSQL")

    # Generate and upsert embeddings to Pinecone
    if os.getenv('PINECONE_API_KEY') and os.getenv('OPENAI_API_KEY'):
        index = init_pinecone()
        batch_size = 100
        upserted = 0
        deduped_data = [item for item in data if item.get('url', '') not in seen_urls or not seen_urls.add(item.get('url', ''))]
        logger.info(f"Processing {len(deduped_data)} unique records for Pinecone")
        for i in range(0, len(deduped_data), batch_size):
            batch = deduped_data[i:i + batch_size]
            vectors = []
            for j, item in enumerate(batch):
                text = f"{item.get('product', '')} {item.get('category', '')} {item.get('issue', '')} {item.get('solution', '')}"
                embedding = generate_embedding(text)
                if embedding:
                    vectors.append((
                        f"snapone_pdf_{i + j}",
                        embedding,
                        {
                            'url': item.get('url', ''),
                            'product': item.get('product', ''),
                            'category': item.get('category', ''),
                            'issue': item.get('issue', ''),
                            'solution': item.get('solution', ''),
                            'brand': 'SnapOne'  # Distinguish from Lutron data
                        }
                    ))
            if vectors:
                try:
                    index.upsert(vectors)
                    upserted += len(vectors)
                    logger.info(f"Upserted {len(vectors)} embeddings to Pinecone")
                except Exception as e:
                    logger.error(f"Failed to upsert batch to Pinecone: {e}")
            time.sleep(1)  # Avoid rate limits
        logger.info(f"Total upserted {upserted} embeddings to Pinecone")
    else:
        logger.warning("Skipping Pinecone upsert: Missing API keys")

    cursor.close()
    conn.close()
    logger.info("Data processing complete")

if __name__ == "__main__":
    process_snapone_data()