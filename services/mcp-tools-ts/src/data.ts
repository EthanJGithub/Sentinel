import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

// data dir: DATA_DIR env (containers mount /data) else repo data/
const DATA_DIR = process.env.DATA_DIR
  ? resolve(process.env.DATA_DIR)
  : resolve(__dirname, "..", "..", "..", "data");

export interface RegChunk {
  id: string;
  source: string;
  citation: string;
  title: string;
  content: string;
  category: string[];
  keywords: string[];
  ftag: string | null;
}

export interface Rule {
  rule_id: string;
  category: string;
  predicate: Record<string, any>;
  citation: string;
  reg_id: string;
  message: string;
  applies_when?: Record<string, any>;
}

export function loadRegs(): RegChunk[] {
  const txt = readFileSync(join(DATA_DIR, "regulations", "regulations.jsonl"), "utf-8");
  return txt
    .split(/\r?\n/)
    .filter((l) => l.trim())
    .map((l) => {
      const d = JSON.parse(l);
      return {
        id: d.id, source: d.source, citation: d.citation, title: d.title,
        content: d.content, category: d.category ?? [], keywords: d.keywords ?? [],
        ftag: d.ftag ?? null,
      } as RegChunk;
    });
}

export function loadRules(): Rule[] {
  const txt = readFileSync(join(DATA_DIR, "catalog", "compliance_rules.json"), "utf-8");
  return JSON.parse(txt) as Rule[];
}

export const regIndex = (chunks: RegChunk[]) =>
  Object.fromEntries(chunks.map((c) => [c.id, c]));
