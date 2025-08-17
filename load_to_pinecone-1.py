import json
import os
import logging
import uuid
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(dotenv_path='/home/vincent/ixome/.env')
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
PINECONE_ENVIRONMENT = os.getenv('PINECONE_ENVIRONMENT')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)
index_name = 'troubleshooter-index'

# Create or update Pinecone index
if index_name in pc.list_indexes().names():
    index_desc = pc.describe_index(index_name)
    if index_desc.dimension != 1536:
        logger.info(f"Deleting and recreating index {index_name} with dimension 1536.")
        pc.delete_index(index_name)
        pc.create_index(
            name=index_name,
            dimension=1536,
            metric='cosine',
            spec=ServerlessSpec(cloud='aws', region=PINECONE_ENVIRONMENT)
        )
else:
    logger.info(f"Creating new index {index_name} with dimension 1536.")
    pc.create_index(
        name=index_name,
        dimension=1536,
        metric='cosine',
        spec=ServerlessSpec(cloud='aws', region=PINECONE_ENVIRONMENT)
    )

index = pc.Index(index_name)

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def get_embedding(text):
    """Generate embedding for text using OpenAI API."""
    if not text.strip():
        return None
    response = openai_client.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

def load_to_pinecone():
    """Load data from JSON file to Pinecone, handling metadata size and JSON errors."""
    try:
        data = []
        json_file = '/home/vincent/ixome/scrapy-selenium/lutron_scraper/lutron_data.json'
        
        # Read and process JSON file
        with open(json_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():  # Skip empty lines
                    try:
                        item = json.loads(line)
                        # Truncate 'solution' to 10,000 characters to stay under 40,960 bytes
                        max_solution_length = 10000
                        solution = item.get('solution', '')
                        if len(solution) > max_solution_length:
                            logger.info(f"Truncated solution for item with url: {item.get('url', 'unknown')}")
                            item['solution'] = solution[:max_solution_length]
                        data.append(item)
                    except json.JSONDecodeError as e:
                        logger.error(f"Skipping malformed JSON line: {line[:50]}... {e}")
                        continue

        # Prepare vectors for Pinecone
        vectors = []
        for item in data:
            text = f"{item.get('issue', '')} {item.get('solution', '')} {item.get('product', '')}"
            embedding = get_embedding(text)
            if embedding is None:
                continue
            vector_id = str(uuid.uuid4())
            vectors.append({
                'id': vector_id,
                'values': embedding,
                'metadata': {
                    'issue': item.get('issue', ''),
                    'solution': item.get('solution', ''),
                    'product': item.get('product', ''),
                    'category': item.get('category', ''),
                    'url': item.get('url', '')
                }
            })

        # Upsert vectors to Pinecone
        if vectors:
            index.upsert(vectors=vectors)
            logger.info(f"Upserted {len(vectors)} vectors to Pinecone index {index_name}")
        else:
            logger.warning("No vectors to upsert")

    except Exception as e:
        logger.error(f"Error loading to Pinecone: {e}")

if __name__ == "__main__":
    load_to_pinecone()