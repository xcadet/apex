import { useEffect, useMemo, useState } from 'react'
import './App.css'
import type { Design, Column } from './types.ts'
import { COLUMNS, NUMERIC_COLUMNS } from './types.ts'
import { loadDesigns } from './lib/data.ts'
import {
  applyFilters,
  buildFacets,
  numericBounds,
  sortDesigns,
  type EnumFilters,
  type NumericFilters,
} from './lib/filters.ts'
import { Filters } from './components/Filters.tsx'
import { DesignTable } from './components/DesignTable.tsx'
import { DetailPanel } from './components/DetailPanel.tsx'

const PAGE_SIZE = 50

function App() {
  const [designs, setDesigns] = useState<Design[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [enumFilters, setEnumFilters] = useState<EnumFilters>({})
  const [numericFilters, setNumericFilters] = useState<NumericFilters>({})
  const [sortKey, setSortKey] = useState<keyof Design>('score')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [page, setPage] = useState(1)
  const [selectedSha1, setSelectedSha1] = useState<string | null>(null)

  // Column display controls.
  const [hiddenCols, setHiddenCols] = useState<Set<string>>(new Set())
  const [columnOrder, setColumnOrder] = useState<string[]>(() => COLUMNS.map((c) => c.key))

  useEffect(() => {
    loadDesigns()
      .then(setDesigns)
      .catch((e: unknown) => setError(String(e)))
  }, [])

  const facets = useMemo(() => buildFacets(designs ?? []), [designs])
  const bounds = useMemo(() => numericBounds(designs ?? []), [designs])

  // Once data is in, widen every numeric range to the data's true bounds.
  useEffect(() => {
    if (designs) setNumericFilters(bounds)
  }, [designs, bounds])

  const filtered = useMemo(
    () => applyFilters(designs ?? [], enumFilters, numericFilters),
    [designs, enumFilters, numericFilters],
  )
  const sorted = useMemo(() => sortDesigns(filtered, sortKey, sortDir), [filtered, sortKey, sortDir])

  // Snap back to page 1 whenever the result set or ordering changes.
  useEffect(() => setPage(1), [enumFilters, numericFilters, sortKey, sortDir])

  const pageCount = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE))
  const clampedPage = Math.min(page, pageCount)
  const pageRows = sorted.slice((clampedPage - 1) * PAGE_SIZE, clampedPage * PAGE_SIZE)

  const selected = selectedSha1 ? (designs?.find((d) => d.sha1 === selectedSha1) ?? null) : null

  // Columns in the user's chosen order, minus the hidden ones.
  const orderedColumns = useMemo(
    () => columnOrder.map((k) => COLUMNS.find((c) => c.key === k)).filter((c): c is Column => !!c),
    [columnOrder],
  )
  const visibleColumns = useMemo(
    () => orderedColumns.filter((c) => !hiddenCols.has(c.key)),
    [orderedColumns, hiddenCols],
  )

  const activeCount =
    Object.values(enumFilters).reduce((n, set) => n + (set?.size ?? 0), 0) +
    NUMERIC_COLUMNS.filter((c) => {
      const r = numericFilters[c.key]
      const b = bounds[c.key]
      return r && b && (r[0] > b[0] || r[1] < b[1])
    }).length

  function toggleEnum(key: string, value: string) {
    setEnumFilters((prev) => {
      const next: EnumFilters = { ...prev }
      const set = new Set(next[key])
      if (set.has(value)) set.delete(value)
      else set.add(value)
      next[key] = set
      return next
    })
  }

  function onSort(key: keyof Design) {
    if (key === sortKey) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else {
      setSortKey(key)
      setSortDir(key === 'score' ? 'desc' : 'asc')
    }
  }

  function setNumericRange(key: string, range: [number, number]) {
    setNumericFilters((prev) => ({ ...prev, [key]: range }))
  }

  function toggleColumn(key: string) {
    setHiddenCols((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  // Move column `fromKey` to the position of `toKey` in the display order.
  function reorderColumns(fromKey: string, toKey: string) {
    if (fromKey === toKey) return
    setColumnOrder((prev) => {
      const next = prev.filter((k) => k !== fromKey)
      const idx = next.indexOf(toKey)
      if (idx === -1) return prev
      next.splice(idx, 0, fromKey)
      return next
    })
  }

  function reset() {
    setEnumFilters({})
    setNumericFilters(bounds)
  }

  if (error) {
    return (
      <div className="app">
        <div className="message error">
          Failed to load data: {error}
          <p>Run <code>npm run export</code> to generate <code>public/data/</code> first.</p>
        </div>
      </div>
    )
  }

  if (!designs) {
    return (
      <div className="app">
        <div className="message">Loading designs…</div>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>⛰️ APEX Design Explorer</h1>
        <span className="count">
          {sorted.length.toLocaleString()} / {designs.length.toLocaleString()} designs
        </span>
      </header>

      <div className="layout">
        <Filters
          facets={facets}
          enumFilters={enumFilters}
          onToggle={toggleEnum}
          numericFilters={numericFilters}
          numericBounds={bounds}
          onNumericChange={setNumericRange}
          hiddenCols={hiddenCols}
          onToggleColumn={toggleColumn}
          activeCount={activeCount}
          onReset={reset}
        />

        <main className="main">
          <div className="toolbar">
            <span className="result-count">
              <strong>{sorted.length.toLocaleString()}</strong> match
            </span>
            <span className="pager">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={clampedPage <= 1}
              >
                ‹ Prev
              </button>
              <span>
                Page {clampedPage} / {pageCount}
              </span>
              <button
                type="button"
                onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
                disabled={clampedPage >= pageCount}
              >
                Next ›
              </button>
            </span>
          </div>

          <DesignTable
            rows={pageRows}
            columns={visibleColumns}
            selectedSha1={selectedSha1}
            onSelect={setSelectedSha1}
            sortKey={sortKey}
            sortDir={sortDir}
            onSort={onSort}
            onReorder={reorderColumns}
          />

          <div className="hint">
            Click a row to open its graph.py / prompt.py · drag a column header to reorder
          </div>
        </main>
      </div>

      {selected && <DetailPanel design={selected} onClose={() => setSelectedSha1(null)} />}
    </div>
  )
}

export default App
