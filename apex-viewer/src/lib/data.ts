import type { Design, Code } from '../types.ts'

const base = import.meta.env.BASE_URL

// All design stats, loaded once on startup (a few MB).
export async function loadDesigns(): Promise<Design[]> {
  const res = await fetch(`${base}data/designs.json`)
  if (!res.ok) throw new Error(`Failed to load designs.json (HTTP ${res.status})`)
  return res.json() as Promise<Design[]>
}

// One design's code, fetched on demand and cached so re-selecting is instant.
const codeCache = new Map<string, Promise<Code>>()

export function loadCode(sha1: string): Promise<Code> {
  let pending = codeCache.get(sha1)
  if (!pending) {
    const url = `${base}data/code/${sha1.slice(0, 2)}/${sha1}.json`
    pending = fetch(url).then((res) => {
      if (!res.ok) throw new Error(`Failed to load code for ${sha1} (HTTP ${res.status})`)
      return res.json() as Promise<Code>
    })
    codeCache.set(sha1, pending)
  }
  return pending
}
