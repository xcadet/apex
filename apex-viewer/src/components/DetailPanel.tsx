import { useEffect, useState } from 'react'
import type { Design, Code } from '../types.ts'
import { COLUMNS } from '../types.ts'
import { loadCode } from '../lib/data.ts'
import { CodeViewer } from './CodeViewer.tsx'

const META_COLUMNS = COLUMNS.filter((c) => c.key !== 'sha1')

export function DetailPanel({ design, onClose }: { design: Design; onClose: () => void }) {
  const [code, setCode] = useState<Code | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<'graph' | 'prompt'>('graph')

  useEffect(() => {
    let active = true
    setCode(null)
    setError(null)
    loadCode(design.sha1)
      .then((c) => active && setCode(c))
      .catch((e: unknown) => active && setError(String(e)))
    return () => {
      active = false
    }
  }, [design.sha1])

  // Esc closes the modal.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="modal" role="dialog" aria-modal="true" aria-label={`Design ${design.sha1}`}>
        <header className="modal-head">
          <div className="modal-meta">
            {META_COLUMNS.map((c) => (
              <span className="chip" key={c.key}>
                <span className="chip-key">{c.label}</span>
                <span className="chip-val">
                  {c.kind === 'numeric'
                    ? (design[c.key] as number).toFixed(c.decimals ?? 2)
                    : String(design[c.key])}
                </span>
              </span>
            ))}
            <code className="chip-sha" title={design.sha1}>
              {design.sha1}
            </code>
          </div>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </header>

        <div className="tabs">
          <button
            type="button"
            className={tab === 'graph' ? 'tab active' : 'tab'}
            onClick={() => setTab('graph')}
          >
            graph.py
          </button>
          <button
            type="button"
            className={tab === 'prompt' ? 'tab active' : 'tab'}
            onClick={() => setTab('prompt')}
          >
            prompt.py
          </button>
        </div>

        <div className="modal-code">
          {error ? (
            <div className="code-empty">{error}</div>
          ) : code === null ? (
            <div className="code-empty">Loading…</div>
          ) : (
            <CodeViewer code={tab === 'graph' ? code.graph : code.prompt} />
          )}
        </div>
      </div>
    </div>
  )
}
