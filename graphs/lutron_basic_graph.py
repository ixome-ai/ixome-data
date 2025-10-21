import os
import subprocess
import json
from dotenv import load_dotenv
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from langgraph.graph import StateGraph, END
from typing import Dict, List, TypedDict
from langchain_openai import OpenAIEmbeddings
from openai import OpenAI
from pinecone import Pinecone as PineconeClient
import psycopg2  # PG direct (replace core.db)

load_dotenv()

embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = PineconeClient(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("troubleshooter-index")

def get_pg_connection():
    return psycopg2.connect(dbname=os.getenv("PG_DBNAME"), user=os.getenv("PG_USER"), password=os.getenv("PG_PASSWORD"), host=os.getenv("PG_HOST", "localhost"), port=os.getenv("PG_PORT", 5432))

def insert_dealer_info(brand, info, component):
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO dealer_info (brand, solution, product) VALUES (%s, %s, %s)", (brand, info, component))
            conn.commit()

def query_sqlite(brand, keyword):  # Stub; use PG query
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT solution FROM dealer_info WHERE brand=%s AND solution ILIKE %s LIMIT 1", (brand, f"%{keyword}%"))
            return cur.fetchone()[0] if cur.fetchone() else 'No match'

class State(TypedDict):
    messages: List[str]
    scraped_data: List[Dict[str, str]]
    filtered_data: List[Dict[str, str]]

def scrape_agent(state: State) -> State:
    scraped_data = []
    spider_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scrapers', 'lutron_scraper', 'lutron_scraper'))
    output_file = '/tmp/lutron_homeworks_items.jsonl'
    try:
        current_dir = os.getcwd()
        os.chdir(spider_dir)
        subprocess.call(['scrapy', 'crawl', 'lutron_homeworks', '-o', output_file], cwd=spider_dir)
        with open(output_file, 'r') as f:
            scraped_data = [json.loads(line) for line in f if line.strip()]
        os.remove(output_file)
        os.chdir(current_dir)
        print("Debug: Scraped sample: ", scraped_data[0] if scraped_data else "No items")
    except Exception as e:
        print(f"Scrapy error: {e}")
    return {"scraped_data": scraped_data, "messages": state["messages"] + ["Scraped Lutron HomeWorks data"]}

def filter_agent(state: State) -> State:
    filtered_data = []
    for item in state["scraped_data"]:
        text = item.get('solution', ' '.join(str(v) for v in item.values()))
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "Filter for Lutron HomeWorks data. 'yes' if relevant to smart home lighting, automation, switches, integration; else 'no'."},
                      {"role": "user", "content": text[:2000]}]  # Trunc for LLM
        )
        if response.choices[0].message.content.lower().strip() == 'yes':
            filtered_data.append(item)
    return {"filtered_data": filtered_data, "messages": state["messages"] + [f"Filtered to {len(filtered_data)} items"]}

def load_agent(state: State) -> State:
    for item in state["filtered_data"]:
        info = item.get('solution', '')
        component = item.get('product', 'HomeWorks')
        insert_dealer_info("Lutron", info, component)
        emb = embeddings.embed_query(info)
        metadata_solution = info[:40000]
        index.upsert([{"id": str(hash(info)), "values": emb, "metadata": {"solution": metadata_solution, "brand": "Lutron", "issue": item.get('issue', ''), "category": item.get('category', ''), "url": item.get('url', ''), "product": component}}])
    return {"messages": state["messages"] + ["Loaded to PG/Pinecone"]}

def query_agent(state: State) -> State:
    emb = embeddings.embed_query("HomeWorks lighting issue")
    results = index.query(vector=emb, top_k=1, include_metadata=True).get('matches', [])
    pinecone_result = results[0].get('metadata', {}).get('solution', '') if results else 'No match'
    pg_result = query_sqlite("Lutron", "lighting")
    combined = f"Pinecone: {pinecone_result[:100]}...\nPG: {pg_result[:100]}..."
    return {"messages": state["messages"] + [combined]}

graph = StateGraph(State)
graph.add_node("scrape", scrape_agent)
graph.add_node("filter", filter_agent)
graph.add_node("load", load_agent)
graph.add_node("query", query_agent)
graph.add_edge("scrape", "filter")
graph.add_edge("filter", "load")
graph.add_edge("load", "query")
graph.add_edge("query", END)
graph.set_entry_point("scrape")
app = graph.compile()

if __name__ == "__main__":
    initial_state = {"messages": [], "scraped_data": [], "filtered_data": []}
    result = app.invoke(initial_state)
    print(result)