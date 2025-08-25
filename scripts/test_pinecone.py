from pinecone import Pinecone
import os
from dotenv import load_dotenv
import openai

load_dotenv('/home/vincent/ixome/.env')
pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
index = pc.Index('troubleshooter-index')
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

queries = ["Touch Screens", "Microphone", "Lutron"]
for query in queries:
    embedding = client.embeddings.create(input=query, model='text-embedding-ada-002').data[0].embedding
    results = index.query(vector=embedding, top_k=2, include_metadata=True)
    print(f"\nQuery: {query}")
    print(results)