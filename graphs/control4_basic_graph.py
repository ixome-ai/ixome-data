import os
import subprocess
import json
from dotenv import load_dotenv  # Fits your existing env loading in chat_agent.py
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # Root path for core/ 
from langgraph.graph import StateGraph, END  # Fits LangGraph 0.2.20 deps
from typing import Dict, List, TypedDict
from langchain_core.messages import HumanMessage
from langchain_openai import OpenAIEmbeddings  # Embeddings fit (dynamic for variable data)
from openai import OpenAI  # Fits your client for filter LLM
from pinecone import Pinecone as PineconeClient  # Fits your pc/init in chat_agent.py
from core.db import insert_dealer_info, query_sqlite  # Hybrid fit from db.py

load_dotenv()

embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")  # Fits your embeddings; dynamic/variable length (Grok 4 placeholder: model="grok-4" when API ready)
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # For filter LLM (fits your client in chat_agent.py)
pc = PineconeClient(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("troubleshooter-index")  # Fits your index

class State(TypedDict):
    messages: List[str]
    scraped_data: List[Dict[str, str]]
    filtered_data: List[Dict[str, str]]

def scrape_agent(state: State) -> State:
    scraped_data = []  # Collect yielded items from JSON
    # Run Scrapy via subprocess (fits your nested path; avoids import issues, preserves spider 100%)
    spider_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scrapy-selenium', 'control4_scraper', 'control4_scraper'))  # Change dir to your project root for run
    output_file = '/tmp/scraped_items.json'  # Temp JSON in /tmp to avoid dir issues
    try:
        current_dir = os.getcwd()  # Save current dir
        os.chdir(spider_dir)  # Change to project dir for crawl (fixes "no active project")
        subprocess.call(['scrapy', 'crawl', 'control4', '-o', output_file])  # Run spider, output to JSON (name 'control4' fits new spider)
        with open(output_file, 'r') as f:
            scraped_data = json.load(f)  # Load yielded items (fits your spider yield dicts)
        os.remove(output_file)  # Clean up
        os.chdir(current_dir)  # Restore dir
        print("Debug: Scraped data keys and sample: ", scraped_data[0] if scraped_data else "No items scraped")  # Debug for keys
    except Exception as e:
        print(f"Scrapy run error: {e}")  # Log; continue with empty for test
    return {"scraped_data": scraped_data, "messages": state["messages"] + ["Scraped Control4 data"]}

def filter_agent(state: State) -> State:
    filtered_data = []  # Only important items (relevant to smart home/racks)
    for item in state["scraped_data"]:
        text = item.get('solution', ' '.join(str(v) for v in item.values()))  # Dynamic text
        # Use LLM to filter important (fits goal: look at everything, add only relevant)
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a filter for Control4 troubleshooting data. Return 'yes' if relevant to smart home automation, equipment racks, switches, receivers, matrix amps, audio, video, routers, TVs, cameras; else 'no'."},
                      {"role": "user", "content": text}]
        )
        if response.choices[0].message.content.lower().strip() == 'yes':
            filtered_data.append(item)
    return {"filtered_data": filtered_data, "messages": state["messages"] + [f"Filtered to {len(filtered_data)} important items"]}

def load_agent(state: State) -> State:
    for item in state["filtered_data"]:
        info = item.get('solution', ' '.join(str(v) for v in item.values()))  # Use 'solution' or concat
        component = item.get('product', 'unknown')  # From your Lutron debug; fits Control4
        insert_dealer_info("Control4", info, component)  # Hybrid to SQLite (full text, no limit)
        # Dynamic upsert to Pinecone (batch for efficiency, variable lengths)
        emb = embeddings.embed_query(info)  # Embed full for search
        metadata_solution = info[:40000]  # Truncate to <40KB for metadata limit (fits Pinecone)
        index.upsert([{"id": str(hash(info)), "values": emb, "metadata": {"solution": metadata_solution, "brand": "Control4", "issue": item.get('issue', ''), "category": item.get('category', ''), "url": item.get('url', ''), "product": component}}])
    return {"messages": state["messages"] + ["Loaded important data to hybrid DB"]}

def query_agent(state: State) -> State:
    # Hybrid query (fits retrieval in chat_agent.py)
    emb = embeddings.embed_query("Control4 rack issue")
    results = index.query(vector=emb, top_k=1, include_metadata=True).get('matches', [])
    pinecone_result = results[0].get('metadata', {}).get('solution', '') if results else 'No Pinecone matches'
    sqlite_result = query_sqlite("Control4", "audio")  # Example; dynamic from input/issue later
    combined = f"Pinecone: {pinecone_result}\nSQLite: {sqlite_result}"
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

# Test block (run standalone: python graphs/control4_basic_graph.py; runs crawl, prints state with scraped + hybrid)
if __name__ == "__main__":
    initial_state = {"messages": [], "scraped_data": [], "filtered_data": []}
    result = app.invoke(initial_state)
    print(result)  # Output: {'messages': ['Scraped Control4 data', 'Filtered to N important items', 'Loaded important data to hybrid DB', 'Pinecone: ... \nSQLite: ...'], 'scraped_data': [...], 'filtered_data': [...]}