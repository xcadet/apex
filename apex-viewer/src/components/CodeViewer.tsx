import { useMemo, useState } from 'react'
import hljs from 'highlight.js/lib/core'
import python from 'highlight.js/lib/languages/python'
import 'highlight.js/styles/github.css'

hljs.registerLanguage('python', python)

// Read-only Python viewer: highlighted source with a sticky line-number gutter.
// (No per-line splitting — triple-quoted strings span lines — so the gutter is a
// parallel column sized to the source's line count and the two scroll together.)
export function CodeViewer({ code }: { code: string }) {
  const html = useMemo(
    () => (code ? hljs.highlight(code, { language: 'python' }).value : ''),
    [code],
  )
  const gutter = useMemo(() => {
    const lines = code ? code.split('\n').length : 1
    return Array.from({ length: lines }, (_, i) => i + 1).join('\n')
  }, [code])

  const [copied, setCopied] = useState(false)
  const copy = () => {
    void navigator.clipboard?.writeText(code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1200)
    })
  }

  if (!code) return <div className="code-empty">(empty)</div>

  return (
    <div className="code-viewer">
      <button type="button" className="copy-btn" onClick={copy}>
        {copied ? 'Copied' : 'Copy'}
      </button>
      <div className="code-scroll">
        <pre className="gutter" aria-hidden="true">
          {gutter}
        </pre>
        <pre className="source">
          <code dangerouslySetInnerHTML={{ __html: html }} />
        </pre>
      </div>
    </div>
  )
}
