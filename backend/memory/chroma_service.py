import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Try importing chromadb, implement a fallback if chromadb or its dependencies fail to load on the local environment
CHROMA_AVAILABLE = False
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except Exception as e:
    logger.warning(f"ChromaDB not fully available or failed to import ({e}). Falling back to JSON-based Vector Emulator.")

DB_DIR = os.path.dirname(os.path.dirname(__file__))
CHROMA_PATH = os.path.join(DB_DIR, "chroma_db")
FALLBACK_FILE = os.path.join(DB_DIR, "chroma_fallback.json")

class ChromaMemoryService:
    def __init__(self):
        self.chroma_client = None
        self.collection = None
        
        if CHROMA_AVAILABLE:
            try:
                os.makedirs(CHROMA_PATH, exist_ok=True)
                self.chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
                self.collection = self.chroma_client.get_or_create_collection(
                    name="voice_action_memory",
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info("ChromaDB persistent client initialized successfully.")
                return
            except Exception as e:
                logger.error(f"Error initializing ChromaDB persistent client: {e}. Falling back to JSON memory.")
        
        # Initialize fallback if ChromaDB is not available or errored
        self._init_fallback()

    def _init_fallback(self):
        logger.info(f"Initializing JSON fallback vector store at: {FALLBACK_FILE}")
        if not os.path.exists(FALLBACK_FILE):
            with open(FALLBACK_FILE, "w") as f:
                json.dump([], f)

    def store_memory(self, user_command: str, summary: str, workflow_plan: list, tool: str, parameters: dict):
        """Stores a workflow run as a semantic memory."""
        metadata = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tool": tool,
            "parameters": json.dumps(parameters),
            "workflow_plan": json.dumps(workflow_plan),
            "summary": summary
        }
        
        if self.collection:
            try:
                # Store memory in ChromaDB
                memory_id = f"mem_{datetime.now().timestamp()}"
                self.collection.add(
                    documents=[user_command],
                    metadatas=[metadata],
                    ids=[memory_id]
                )
                logger.info(f"Successfully stored command '{user_command}' in ChromaDB.")
                return
            except Exception as e:
                logger.error(f"Failed to store in ChromaDB ({e}). Trying fallback storage.")

        # Fallback Storage
        try:
            with open(FALLBACK_FILE, "r") as f:
                memories = json.load(f)
            
            memories.append({
                "id": f"mem_{datetime.now().timestamp()}",
                "document": user_command,
                "metadata": metadata
            })
            
            with open(FALLBACK_FILE, "w") as f:
                json.dump(memories, f, indent=2)
            logger.info(f"Successfully stored command '{user_command}' in JSON fallback memory.")
        except Exception as e:
            logger.error(f"Failed to store in fallback JSON database ({e}).")

    def search_memory(self, query: str, limit: int = 2) -> list:
        """Searches memories semantically based on user query."""
        if self.collection:
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=limit
                )
                
                formatted_results = []
                if results and 'documents' in results and results['documents']:
                    for i in range(len(results['documents'][0])):
                        doc = results['documents'][0][i]
                        meta = results['metadatas'][0][i]
                        formatted_results.append({
                            "command": doc,
                            "timestamp": meta.get("timestamp"),
                            "tool": meta.get("tool"),
                            "parameters": json.loads(meta.get("parameters", "{}")),
                            "workflow_plan": json.loads(meta.get("workflow_plan", "[]")),
                            "summary": meta.get("summary"),
                            "similarity": 1.0  # ChromaDB query contains distance
                        })
                return formatted_results
            except Exception as e:
                logger.error(f"ChromaDB search failed ({e}). Falling back to substring search.")

        # Fallback substring-based search (and mock semantic relevance)
        try:
            with open(FALLBACK_FILE, "r") as f:
                memories = json.load(f)
            
            # Simple keyword matching to simulate semantic matching
            query_words = set(query.lower().split())
            scored_memories = []
            
            for mem in memories:
                doc_lower = mem["document"].lower()
                # Score based on keyword overlap
                matches = sum(1 for word in query_words if word in doc_lower)
                # Extra points for exact or partial phrase matching
                if query.lower() in doc_lower:
                    matches += 5
                
                if matches > 0:
                    meta = mem["metadata"]
                    scored_memories.append((matches, {
                        "command": mem["document"],
                        "timestamp": meta.get("timestamp"),
                        "tool": meta.get("tool"),
                        "parameters": json.loads(meta.get("parameters", "{}")),
                        "workflow_plan": json.loads(meta.get("workflow_plan", "[]")),
                        "summary": meta.get("summary"),
                        "similarity": min(1.0, 0.5 + (matches * 0.1))
                    }))
            
            # Sort by score descending
            scored_memories.sort(key=lambda x: x[0], reverse=True)
            return [item[1] for item in scored_memories[:limit]]
            
        except Exception as e:
            logger.error(f"JSON fallback search failed ({e}). Returning empty list.")
            return []

# Singleton instance
memory_service = ChromaMemoryService()
