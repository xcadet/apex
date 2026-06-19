import { useState } from 'react'
import { ENUM_COLUMNS, NUMERIC_COLUMNS } from '../types.ts'
import type { EnumFilters, NumericFilters } from '../lib/filters.ts'

interface Props {
  facets: Record<string, string[]>
  enumFilters: EnumFilters
  onToggle: (key: string, value: string) => void
  numericFilters: NumericFilters
  numericBounds: NumericFilters
  onNumericChange: (key: string, range: [number, number]) => void
  hiddenCols: Set<string>
  onToggleColumn: (key: string) => void
  activeCount: number
  onReset: () => void
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      className={`chev${open ? ' open' : ''}`}
      viewBox="0 0 24 24"
      width="12"
      height="12"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      aria-hidden="true"
    >
      <polyline points="9 6 15 12 9 18" />
    </svg>
  )
}

function EyeIcon({ off }: { off: boolean }) {
  return off ? (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20C5 20 1 12 1 12a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  ) : (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

export function Filters({
  facets,
  enumFilters,
  onToggle,
  numericFilters,
  numericBounds,
  onNumericChange,
  hiddenCols,
  onToggleColumn,
  activeCount,
  onReset,
}: Props) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())
  const groupKeys = [...NUMERIC_COLUMNS, ...ENUM_COLUMNS].map((c) => c.key)

  function toggleCollapse(key: string) {
    setCollapsed((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  function groupHead(key: string, label: string, badge?: number) {
    const isOpen = !collapsed.has(key)
    const isHidden = hiddenCols.has(key)
    return (
      <div className="group-head">
        <button type="button" className="fold-btn" onClick={() => toggleCollapse(key)} aria-expanded={isOpen}>
          <Chevron open={isOpen} />
          <span className="group-name">{label}</span>
          {badge ? <span className="badge">{badge}</span> : null}
        </button>
        <button
          type="button"
          className={`eye-btn${isHidden ? ' off' : ''}`}
          onClick={() => onToggleColumn(key)}
          title={isHidden ? `Show "${label}" column` : `Hide "${label}" column`}
          aria-label={isHidden ? `Show ${label} column` : `Hide ${label} column`}
        >
          <EyeIcon off={isHidden} />
        </button>
      </div>
    )
  }

  return (
    <aside className="filters">
      <div className="filters-head">
        <h2>Filters</h2>
        <button type="button" className="link-btn" onClick={onReset} disabled={activeCount === 0}>
          Reset{activeCount > 0 ? ` (${activeCount})` : ''}
        </button>
      </div>
      <div className="filters-tools">
        <button type="button" className="link-btn" onClick={() => setCollapsed(new Set())}>
          Expand all
        </button>
        <span className="sep">·</span>
        <button type="button" className="link-btn" onClick={() => setCollapsed(new Set(groupKeys))}>
          Collapse all
        </button>
      </div>

      {NUMERIC_COLUMNS.map((col) => {
        const [bLo, bHi] = numericBounds[col.key] ?? [0, 1]
        const [lo, hi] = numericFilters[col.key] ?? [bLo, bHi]
        const step = col.step ?? 0.01
        const dec = col.decimals ?? 2
        return (
          <div className="filter-group" key={col.key}>
            {groupHead(col.key, col.label)}
            {!collapsed.has(col.key) && (
              <div className="group-body">
                <div className="score-readout">
                  {lo.toFixed(dec)} – {hi.toFixed(dec)}
                </div>
                <input
                  type="range"
                  min={bLo}
                  max={bHi}
                  step={step}
                  value={lo}
                  onChange={(e) => onNumericChange(col.key, [Math.min(Number(e.target.value), hi), hi])}
                />
                <input
                  type="range"
                  min={bLo}
                  max={bHi}
                  step={step}
                  value={hi}
                  onChange={(e) => onNumericChange(col.key, [lo, Math.max(Number(e.target.value), lo)])}
                />
              </div>
            )}
          </div>
        )
      })}

      {ENUM_COLUMNS.map((col) => {
        const values = facets[col.key] ?? []
        const selected = enumFilters[col.key]
        return (
          <div className="filter-group" key={col.key}>
            {groupHead(col.key, col.label, selected?.size)}
            {!collapsed.has(col.key) && (
              <div className="group-body">
                <div className="checkbox-list">
                  {values.map((v) => (
                    <label key={v} className="checkbox-row">
                      <input
                        type="checkbox"
                        checked={selected?.has(v) ?? false}
                        onChange={() => onToggle(col.key, v)}
                      />
                      <span>{v}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        )
      })}
    </aside>
  )
}
