import type { RegChunk } from "./data.js";

// Lightweight TF-IDF-ish keyword retriever — mirrors the Python LocalKeywordRetriever
// so reg_search behaves identically whether the agent calls the MCP server or the
// in-process Python fallback. Deterministic, no embeddings, $0.

const tok = (s: string): string[] => (s.toLowerCase().match(/[a-z0-9]{3,}/g) ?? []);

export class KeywordRetriever {
  private docs: string[][];
  private df: Record<string, number> = {};
  private N: number;

  constructor(private chunks: RegChunk[]) {
    this.docs = chunks.map((c) => tok([c.title, c.content, c.keywords.join(" "), c.category.join(" ")].join(" ")));
    for (const toks of this.docs) {
      for (const w of new Set(toks)) this.df[w] = (this.df[w] ?? 0) + 1;
    }
    this.N = Math.max(1, chunks.length);
  }

  private idf(w: string): number {
    return Math.log((this.N + 1) / ((this.df[w] ?? 0) + 1)) + 1;
  }

  search(query: string, categories: string[] = [], k = 4) {
    const q = new Set([...tok(query), ...categories.flatMap(tok)]);
    const scored = this.chunks.map((c, i) => {
      const toks = this.docs[i];
      const tf: Record<string, number> = {};
      for (const w of toks) tf[w] = (tf[w] ?? 0) + 1;
      let s = 0;
      for (const w of q) s += (tf[w] ?? 0) * this.idf(w);
      if (categories.length && categories.some((cat) => c.category.includes(cat))) s *= 1.8;
      const norm = s / (1 + Math.log(1 + toks.length));
      return { chunk: c, score: Math.round(norm * 1e4) / 1e4 };
    });
    return scored.filter((r) => r.score > 0).sort((a, b) => b.score - a.score).slice(0, k);
  }
}
