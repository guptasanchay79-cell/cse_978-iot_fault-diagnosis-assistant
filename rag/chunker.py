"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Module: rag/chunker.py
Section-aware document chunker for technical Markdown manuals in knowledge_base/.
Splits documents by logical engineering sections (Symptoms, Causes, Checks, Actions, Safety)
while preserving document metadata and contextual headers.
"""

from dataclasses import asdict, dataclass
import logging
from pathlib import Path
import re
import sys
from typing import List

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import KNOWLEDGE_BASE_DIR

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("RAGChunker")


@dataclass
class KnowledgeChunk:
    """Represents a discrete semantic chunk of a technical diagnostic document."""

    chunk_id: str
    doc_id: str
    doc_title: str
    section_title: str
    content: str
    source_file: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @property
    def searchable_text(self) -> str:
        """Full text representation used for indexing and semantic similarity matching."""
        return f"{self.doc_title}\nSection: {self.section_title}\n{self.content}"


def parse_markdown_document(file_path: Path) -> List[KnowledgeChunk]:
    """Parse a single Markdown manual into section-based KnowledgeChunks."""
    text = file_path.read_text(encoding="utf-8")
    doc_id = file_path.stem

    # Extract Document Title from first # heading
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    doc_title = title_match.group(1).strip() if title_match else doc_id

    # Split document by Level-2 headings (## ...)
    sections = re.split(r"\n(?=##\s+)", text)
    chunks: List[KnowledgeChunk] = []

    for idx, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue

        lines = section.split("\n", 1)
        header_line = lines[0].strip()

        if header_line.startswith("## "):
            section_title = header_line.replace("## ", "").strip()
            # Clean numbered prefix e.g. '1. Diagnostic Symptoms' -> 'Diagnostic Symptoms'
            section_title = re.sub(r"^\d+\.\s*", "", section_title)
            body = lines[1].strip() if len(lines) > 1 else ""
        else:
            section_title = "Overview & Metadata"
            body = section

        # Format chunk content with document title context
        chunk_content = f"Asset Diagnostic Manual: {doc_title}\nSection: {section_title}\n\n{body}"
        chunk_id = f"{doc_id}_s{idx:02d}"

        chunks.append(
            KnowledgeChunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                doc_title=doc_title,
                section_title=section_title,
                content=chunk_content,
                source_file=file_path.name,
            )
        )

    return chunks


def load_and_chunk_knowledge_base(kb_dir: Path = KNOWLEDGE_BASE_DIR) -> List[KnowledgeChunk]:
    """Load and chunk all Markdown technical manuals from the knowledge base directory."""
    if not kb_dir.exists():
        logger.error("Knowledge base directory does not exist: %s", kb_dir)
        return []

    md_files = sorted(kb_dir.glob("*.md"))
    all_chunks: List[KnowledgeChunk] = []

    for file_path in md_files:
        chunks = parse_markdown_document(file_path)
        all_chunks.extend(chunks)

    logger.info(
        "Chunked %d technical documents into %d semantic knowledge chunks.",
        len(md_files),
        len(all_chunks),
    )
    return all_chunks
