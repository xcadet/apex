import { useState } from 'react'
import type { Design, Column } from '../types.ts'

interface Props {
  rows: Design[]
  columns: Column[]
  selectedSha1: string | null
  onSelect: (sha1: string) => void
  sortKey: keyof Design
  sortDir: 'asc' | 'desc'
  onSort: (key: keyof Design) => void
  onReorder: (fromKey: string, toKey: string) => void
}

function formatCell(d: Design, col: Column): string {
  if (col.key === 'sha1') return d.sha1.slice(0, 10)
  if (col.kind === 'numeric') return (d[col.key] as number).toFixed(col.decimals ?? 2)
  return String(d[col.key])
}

export function DesignTable({
  rows,
  columns,
  selectedSha1,
  onSelect,
  sortKey,
  sortDir,
  onSort,
  onReorder,
}: Props) {
  const [dragKey, setDragKey] = useState<string | null>(null)
  const [overKey, setOverKey] = useState<string | null>(null)

  return (
    <div className="table-wrap">
      <table className="design-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={[
                  'sortable',
                  col.kind === 'numeric' ? 'num' : '',
                  overKey === col.key && dragKey !== col.key ? 'drop-target' : '',
                  dragKey === col.key ? 'dragging' : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
                draggable
                title="Click to sort · drag to reorder"
                onClick={() => onSort(col.key)}
                onDragStart={() => setDragKey(col.key)}
                onDragOver={(e) => {
                  e.preventDefault()
                  if (overKey !== col.key) setOverKey(col.key)
                }}
                onDrop={(e) => {
                  e.preventDefault()
                  if (dragKey) onReorder(dragKey, col.key)
                  setDragKey(null)
                  setOverKey(null)
                }}
                onDragEnd={() => {
                  setDragKey(null)
                  setOverKey(null)
                }}
              >
                <span className="th-label">
                  <span className="grip" aria-hidden="true">⠿</span>
                  {col.label}
                  {sortKey === col.key ? (
                    <span className="arrow">{sortDir === 'asc' ? '▲' : '▼'}</span>
                  ) : null}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((d) => (
            <tr
              key={d.sha1}
              className={d.sha1 === selectedSha1 ? 'selected' : ''}
              onClick={() => onSelect(d.sha1)}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={col.kind === 'numeric' ? 'num' : ''}
                  title={col.key === 'sha1' ? d.sha1 : undefined}
                >
                  {col.key === 'sha1' ? <code>{formatCell(d, col)}</code> : formatCell(d, col)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
