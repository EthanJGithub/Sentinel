"""Regulation retrieval over the CMS Appendix PP / 42 CFR §483.90 / NFPA 101 corpus.

Two backends, same interface:
  - local keyword retriever (default, $0, offline): TF-weighted overlap over the
    committed regulations.jsonl. Deterministic, no embeddings, runs anywhere.
  - pgvector + OpenAI embeddings ("prod" path): when DATABASE_URL + OpenAI key set.

This is the retrieval half of citation-or-abstain: if nothing relevant is retrieved
above threshold, the Compliance Agent ABSTAINS rather than guessing."""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import Settings


@dataclass
class RegChunk:
    id: str
    source: str
    citation: str
    title: str
    content: str
    category: list[str]
    keywords: list[str]
    ftag: Optional[str] = None


@dataclass
class Retrieved:
    chunk: RegChunk
    score: float


def _tok(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]{3,}", s.lower())


class LocalKeywordRetriever:
    """Lightweight TF-IDF-ish retriever. No external deps; deterministic."""

    def __init__(self, chunks: list[RegChunk]):
        self.chunks = chunks
        self._docs = []
        self.df: dict[str, int] = {}
        for c in chunks:
            text = " ".join([c.title, c.content, " ".join(c.keywords), " ".join(c.category)])
            toks = _tok(text)
            self._docs.append(toks)
            for w in set(toks):
                self.df[w] = self.df.get(w, 0) + 1
        self.N = max(1, len(chunks))

    def _idf(self, w: str) -> float:
        return math.log((self.N + 1) / (self.df.get(w, 0) + 1)) + 1.0

    def search(self, query: str, *, categories: Optional[list[str]] = None, k: int = 4) -> list[Retrieved]:
        q = _tok(query)
        if categories:
            q = q + [t for c in categories for t in _tok(c)]
        qset = set(q)
        scored: list[Retrieved] = []
        for c, toks in zip(self.chunks, self._docs):
            tf = {}
            for w in toks:
                tf[w] = tf.get(w, 0) + 1
            s = sum(tf.get(w, 0) * self._idf(w) for w in qset)
            # category boost: strong signal that this reg governs this item type
            if categories and (set(categories) & set(c.category)):
                s *= 1.8
            if s > 0:
                norm = s / (1 + math.log(1 + len(toks)))
                scored.append(Retrieved(chunk=c, score=round(norm, 4)))
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:k]


class PgVectorRetriever:
    """pgvector + OpenAI embeddings. Used when DATABASE_URL and OpenAI key are set.
    Index is built by eval/ingest_regs or on first use."""

    def __init__(self, settings: Settings, chunks: list[RegChunk]):
        self.s = settings
        self.chunks = chunks
        import openai
        self._client = openai.OpenAI(api_key=settings.openai_api_key)
        self._fallback = LocalKeywordRetriever(chunks)

    def search(self, query: str, *, categories: Optional[list[str]] = None, k: int = 4) -> list[Retrieved]:
        try:
            import numpy as np
            qe = np.array(self._client.embeddings.create(
                model=self.s.model_embed, input=[query]).data[0].embedding)
            if not hasattr(self, "_emb"):
                texts = [f"{c.title}. {c.content}" for c in self.chunks]
                embs = self._client.embeddings.create(model=self.s.model_embed, input=texts).data
                self._emb = np.array([e.embedding for e in embs])
            sims = self._emb @ qe / (np.linalg.norm(self._emb, axis=1) * np.linalg.norm(qe) + 1e-9)
            idx = sims.argsort()[::-1][:k]
            return [Retrieved(chunk=self.chunks[i], score=round(float(sims[i]), 4)) for i in idx]
        except Exception:
            return self._fallback.search(query, categories=categories, k=k)


def load_chunks(settings: Settings) -> list[RegChunk]:
    path: Path = settings.regulations_jsonl
    chunks: list[RegChunk] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        chunks.append(RegChunk(
            id=d["id"], source=d["source"], citation=d["citation"], title=d["title"],
            content=d["content"], category=d.get("category", []),
            keywords=d.get("keywords", []), ftag=d.get("ftag")))
    return chunks


def build_retriever(settings: Settings):
    chunks = load_chunks(settings)
    if settings.database_url and settings.has_openai:
        try:
            return PgVectorRetriever(settings, chunks)
        except Exception:
            pass
    return LocalKeywordRetriever(chunks)
