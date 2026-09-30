"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Module: rag/retriever.py
Local, dependency-free semantic knowledge retrieval engine using the
Vector Space Model with sub-linear TF-IDF weighting and Cosine Similarity.
Provides deterministic, explainable ranking over technical knowledge chunks,
with automatic index persistence and cache invalidation.
"""

import argparse
from collections import Counter
import hashlib
import json
import logging
import math
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import KNOWLEDGE_BASE_DIR, RAG_SIMILARITY_THRESHOLD, RAG_TOP_K
from rag.chunker import KnowledgeChunk, load_and_chunk_knowledge_base

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("RAGRetriever")

# Common English and domain stopwords
STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "should", "shouldn't", "so", "some", "such", "than", "that", "the", "their",
    "theirs", "them", "themselves", "then", "there", "there's", "these", "they",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what",
    "when", "where", "which", "while", "who", "whom", "why", "with", "won't",
    "would", "wouldn't", "you", "your", "yours", "yourself", "yourselves",
}

INDEX_CACHE_DIR = _PROJECT_ROOT / "rag" / "index_cache"
INDEX_CACHE_FILE = INDEX_CACHE_DIR / "tfidf_index.json"


def tokenize(text: str) -> List[str]:
    """Tokenize and normalize text into clean lowercased alphameric terms."""
    # Convert special symbols like °C to 'c', numbers to clean terms
    cleaned = text.lower().replace("°c", " c ").replace("celsius", " c ")
    # Match alphanumeric words of length >= 2
    tokens = re.findall(r"\b[a-z0-9_\-\.]{2,}\b", cleaned)
    # Strip boundary punctuation and filter stopwords
    result: List[str] = []
    for tok in tokens:
        clean_tok = tok.strip(".-_")
        if clean_tok and clean_tok not in STOPWORDS and len(clean_tok) >= 2:
            result.append(clean_tok)
    return result


def compute_directory_hash(kb_dir: Path) -> str:
    """Compute an aggregate hash of all .md files in knowledge_base/ to detect changes."""
    hasher = hashlib.sha256()
    md_files = sorted(kb_dir.glob("*.md"))
    for f in md_files:
        hasher.update(f.name.encode("utf-8"))
        hasher.update(f.read_bytes())
    return hasher.hexdigest()


class TFIDFRetriever:
    """Vector Space Information Retrieval engine using TF-IDF and Cosine Similarity."""

    def __init__(self, kb_dir: Path = KNOWLEDGE_BASE_DIR) -> None:
        self.kb_dir = kb_dir
        self.chunks: List[KnowledgeChunk] = []
        self.chunk_tokens: List[List[str]] = []
        self.doc_freq: Counter[str] = Counter()
        self.num_chunks: int = 0
        self.chunk_weights: List[Dict[str, float]] = []
        self.chunk_norms: List[float] = []

        self._ensure_index_loaded()

    def _ensure_index_loaded(self) -> None:
        """Load index from cache if valid, otherwise build and save."""
        current_hash = compute_directory_hash(self.kb_dir)

        if INDEX_CACHE_FILE.exists():
            try:
                cached_data = json.loads(INDEX_CACHE_FILE.read_text(encoding="utf-8"))
                if cached_data.get("kb_hash") == current_hash:
                    self._deserialize_index(cached_data)
                    logger.info("Loaded cached RAG TF-IDF index (%d chunks).", self.num_chunks)
                    return
            except Exception as exc:
                logger.warning("Failed to load cached index: %s. Rebuilding...", exc)

        logger.info("Building fresh RAG TF-IDF index from %s...", self.kb_dir)
        self._build_index(current_hash)
        self._save_index(current_hash)

    def _build_index(self, current_hash: str) -> None:
        """Build TF-IDF vectors and norms for all knowledge chunks."""
        self.chunks = load_and_chunk_knowledge_base(self.kb_dir)
        self.num_chunks = len(self.chunks)
        self.chunk_tokens = [tokenize(c.searchable_text) for c in self.chunks]

        # Calculate Document Frequency (DF)
        self.doc_freq = Counter()
        for tokens in self.chunk_tokens:
            unique_terms = set(tokens)
            self.doc_freq.update(unique_terms)

        # Build TF-IDF weight vectors and calculate Euclidean norms
        self.chunk_weights = []
        self.chunk_norms = []

        for tokens in self.chunk_tokens:
            term_counts = Counter(tokens)
            weights: Dict[str, float] = {}
            squared_sum = 0.0

            for term, count in term_counts.items():
                df = self.doc_freq.get(term, 0)
                # Sub-linear TF * Smooth IDF
                tf = 1.0 + math.log(count)
                idf = math.log((1.0 + self.num_chunks) / (1.0 + df)) + 1.0
                w = tf * idf
                weights[term] = w
                squared_sum += w * w

            norm = math.sqrt(squared_sum) if squared_sum > 0 else 1.0
            self.chunk_weights.append(weights)
            self.chunk_norms.append(norm)

        logger.info(
            "Indexed %d chunks with %d unique vocabulary terms.",
            self.num_chunks,
            len(self.doc_freq),
        )

    def _save_index(self, current_hash: str) -> None:
        """Persist index to JSON cache file."""
        INDEX_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        serialized = {
            "kb_hash": current_hash,
            "doc_freq": dict(self.doc_freq),
            "num_chunks": self.num_chunks,
            "chunks": [c.to_dict() for c in self.chunks],
            "chunk_weights": self.chunk_weights,
            "chunk_norms": self.chunk_norms,
        }
        INDEX_CACHE_FILE.write_text(json.dumps(serialized, indent=2), encoding="utf-8")
        logger.info("Saved RAG index cache to %s", INDEX_CACHE_FILE)

    def _deserialize_index(self, data: dict) -> None:
        """Restore in-memory index from cached dictionary."""
        self.num_chunks = data["num_chunks"]
        self.doc_freq = Counter(data["doc_freq"])
        self.chunks = [
            KnowledgeChunk(
                chunk_id=c["chunk_id"],
                doc_id=c["doc_id"],
                doc_title=c["doc_title"],
                section_title=c["section_title"],
                content=c["content"],
                source_file=c["source_file"],
            )
            for c in data["chunks"]
        ]
        self.chunk_weights = data["chunk_weights"]
        self.chunk_norms = data["chunk_norms"]

    def retrieve(
        self,
        query: str,
        top_k: int = RAG_TOP_K,
        min_threshold: float = RAG_SIMILARITY_THRESHOLD,
    ) -> List[Dict[str, Any]]:
        """Compute Cosine Similarity between query vector and all chunks.

        Returns:
            Top-K ranked chunks with score, doc_id, section_title, and content.
        """
        query_tokens = tokenize(query)
        if not query_tokens:
            logger.warning("Empty token stream for query: %r", query)
            return []

        query_counts = Counter(query_tokens)
        query_weights: Dict[str, float] = {}
        query_squared_sum = 0.0

        for term, count in query_counts.items():
            df = self.doc_freq.get(term, 0)
            tf = 1.0 + math.log(count)
            idf = math.log((1.0 + self.num_chunks) / (1.0 + df)) + 1.0
            w = tf * idf
            query_weights[term] = w
            query_squared_sum += w * w

        query_norm = math.sqrt(query_squared_sum) if query_squared_sum > 0 else 1.0

        # Calculate Cosine Similarities
        scores: List[Tuple[int, float]] = []
        for idx in range(self.num_chunks):
            weights = self.chunk_weights[idx]
            norm = self.chunk_norms[idx]

            # Dot product between query and chunk
            dot_product = sum(
                query_weights[term] * weights[term]
                for term in query_weights
                if term in weights
            )
            if dot_product > 0:
                sim = dot_product / (query_norm * norm)
                scores.append((idx, sim))

        # Sort descending by similarity score
        scores.sort(key=lambda x: x[1], reverse=True)

        results: List[Dict[str, Any]] = []
        for idx, score in scores[:top_k]:
            chunk = self.chunks[idx]
            results.append(
                {
                    "rank": len(results) + 1,
                    "chunk_id": chunk.chunk_id,
                    "doc_id": chunk.doc_id,
                    "doc_title": chunk.doc_title,
                    "section_title": chunk.section_title,
                    "source_file": chunk.source_file,
                    "score": round(score, 4),
                    "content": chunk.content,
                }
            )

        return results


def main() -> int:
    """CLI testing tool: type a symptom sentence and inspect ranked knowledge chunks."""
    parser = argparse.ArgumentParser(
        description="P_311 Local RAG Knowledge Base Retriever"
    )
    parser.add_argument(
        "--query",
        type=str,
        default="Industrial centrifugal pump exhibits critical bearing vibration of 6.2 mm/s and frictional temperature rise of 67.5 C",
        help="Symptom query to search against the knowledge base",
    )
    parser.add_argument(
        "--top-k", type=int, default=RAG_TOP_K, help="Number of chunks to return (default: 3)"
    )

    args = parser.parse_args()
    retriever = TFIDFRetriever()

    print(f"\nSearching Knowledge Base for: {args.query!r}\n" + "=" * 70)
    results = retriever.retrieve(args.query, top_k=args.top_k)

    if not results:
        print("No matching knowledge documents found.")
        return 0

    for res in results:
        print(
            f"Rank #{res['rank']} | Score: {res['score']:.4f} | Source: {res['source_file']}"
        )
        print(f"Title: {res['doc_title']} -> Section: {res['section_title']}")
        # Print snippet of content
        snippet_lines = res["content"].split("\n")[:5]
        print("Snippet:\n  " + "\n  ".join(snippet_lines))
        print("-" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
