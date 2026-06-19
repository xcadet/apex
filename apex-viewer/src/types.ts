// One discovered design — the stat columns from all_workflows.jsonl (no code).
export interface Design {
  sha1: string
  split: string
  category: string
  dataset: string
  difficulty: string
  score: number
  cost: number
  round: number
  optimizer_model: string
  aggregator_model: string
  worker_model: string
}

// A design's code, lazy-loaded from data/code/<xx>/<sha1>.json.
export interface Code {
  graph: string
  prompt: string
}

export type ColumnKind = 'id' | 'enum' | 'numeric'

export interface Column {
  key: keyof Design
  label: string
  kind: ColumnKind
  step?: number // numeric columns: range-slider granularity
  decimals?: number // numeric columns: display precision
}

// Drives both the table columns and (for enum/numeric) the sidebar filters.
export const COLUMNS: Column[] = [
  { key: 'dataset', label: 'dataset', kind: 'enum' },
  { key: 'category', label: 'category', kind: 'enum' },
  { key: 'difficulty', label: 'difficulty', kind: 'enum' },
  { key: 'split', label: 'split', kind: 'enum' },
  { key: 'score', label: 'score', kind: 'numeric', step: 0.01, decimals: 3 },
  { key: 'cost', label: 'cost ($)', kind: 'numeric', step: 0.01, decimals: 4 },
  { key: 'round', label: 'round', kind: 'numeric', step: 1, decimals: 0 },
  { key: 'optimizer_model', label: 'optimizer', kind: 'enum' },
  { key: 'aggregator_model', label: 'aggregator', kind: 'enum' },
  { key: 'worker_model', label: 'worker', kind: 'enum' },
  { key: 'sha1', label: 'sha1', kind: 'id' },
]

export const ENUM_COLUMNS = COLUMNS.filter((c) => c.kind === 'enum')
export const NUMERIC_COLUMNS = COLUMNS.filter((c) => c.kind === 'numeric')
