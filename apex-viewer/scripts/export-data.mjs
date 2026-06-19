// Split all_workflows.jsonl -> static JSON the Vite app serves.
//
//   public/data/designs.json          stats for every design (no code) — loaded once on startup
//   public/data/code/<xx>/<sha1>.json one design's { graph, prompt } — fetched only when selected
//
// all_workflows.jsonl is the source of truth (one design per line, stats + graph + prompt
// inline). A static site can't ship the 117 MB file to the browser, so we split it: a few-MB
// stats file the app loads up front, and one tiny code file per design so a design's ~4 KB of
// code is fetched only when it's clicked. Files are nested under a 2-char sha1 prefix dir to
// keep any single directory small. Pure Node — no Python, no sqlite, no demo.
//
//   DESIGNS_JSONL=/path/to/all_workflows.jsonl node scripts/export-data.mjs

import { createReadStream, mkdirSync, writeFileSync, rmSync, existsSync } from 'node:fs'
import { createInterface } from 'node:readline'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')

// Stat columns kept in designs.json (everything but the two code blobs).
const STAT_COLS = [
  'sha1', 'split', 'category', 'dataset', 'difficulty', 'score', 'cost', 'round',
  'optimizer_model', 'aggregator_model', 'worker_model',
]
const NUMERIC_COLS = new Set(['score', 'cost', 'round']) // coerce so they sort/slide

const jsonlPath = [
  process.env.DESIGNS_JSONL,
  join(root, 'all_workflows.jsonl'),
  join(root, '..', 'all_workflows.jsonl'),
].find((p) => p && existsSync(p))

if (!jsonlPath) {
  console.error(
    'all_workflows.jsonl not found. Set DESIGNS_JSONL=/path/to/all_workflows.jsonl, ' +
      'place it at apex-viewer/all_workflows.jsonl, or unzip all_workflows.zip at the repo root.',
  )
  process.exit(1)
}

// OUT_DIR lets the container write straight into nginx's web root; defaults to the
// dev location public/data/.
const outDir = process.env.OUT_DIR || join(root, 'public', 'data')
const codeDir = join(outDir, 'code')
rmSync(outDir, { recursive: true, force: true })
mkdirSync(codeDir, { recursive: true })

console.log(`Reading ${jsonlPath}`)
const stats = []
const madeDirs = new Set()

const rl = createInterface({ input: createReadStream(jsonlPath), crlfDelay: Infinity })
for await (const line of rl) {
  if (!line.trim()) continue
  const d = JSON.parse(line)

  const stat = {}
  for (const c of STAT_COLS) stat[c] = NUMERIC_COLS.has(c) ? Number(d[c]) : d[c]
  stats.push(stat)

  const prefix = d.sha1.slice(0, 2)
  if (!madeDirs.has(prefix)) {
    mkdirSync(join(codeDir, prefix), { recursive: true })
    madeDirs.add(prefix)
  }
  writeFileSync(
    join(codeDir, prefix, `${d.sha1}.json`),
    JSON.stringify({ graph: d.graph ?? '', prompt: d.prompt ?? '' }),
  )
}

writeFileSync(join(outDir, 'designs.json'), JSON.stringify(stats))
console.log(`Wrote designs.json (${stats.length.toLocaleString()} designs)`)
console.log(`Wrote ${stats.length.toLocaleString()} per-design code files to data/code/`)
