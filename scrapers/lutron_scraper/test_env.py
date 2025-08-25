import os
from dotenv import load_dotenv

# Load the .env file from the parent directory
load_dotenv('/home/vincent/ixome/.env')

# Retrieve and print the Pinecone API key
pinecone_api_key = os.getenv('PINECONE_API_KEY')
if pinecone_api_key:
    print("Pinecone API key loaded successfully:", pinecone_api_key)
else:
    print("Error: PINECONE_API_KEY not found in .env file!")
