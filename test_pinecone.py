import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

# Load the .env file
load_dotenv('/home/vincent/ixome/.env')

# Retrieve Pinecone API key
pinecone_api_key = os.getenv('PINECONE_API_KEY')
if not pinecone_api_key:
    print("Error: PINECONE_API_KEY not found in .env file!")
    exit()

# Initialize Pinecone client
pinecone = Pinecone(api_key=pinecone_api_key)

# Define index parameters
index_name = 'lutron-support'
dimension = 1536  # Matches OpenAI's text-embedding-ada-002
metric = 'cosine'

# Check if index exists; create it if not
if index_name not in pinecone.list_indexes().names():
    print(f"Index '{index_name}' does not exist. Creating it now...")
    pinecone.create_index(
        name=index_name,
        dimension=dimension,
        metric=metric,
        spec=ServerlessSpec(cloud='aws', region='us-east-1')
    )
    print(f"Index '{index_name}' created successfully.")
else:
    print(f"Index '{index_name}' already exists.")

# Connect to the index and check stats
index = pinecone.Index(index_name)
stats = index.describe_index_stats()
print("Index stats:", stats)

