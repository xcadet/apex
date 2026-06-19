import type { Design } from '../types.ts'
import { ENUM_COLUMNS, NUMERIC_COLUMNS } from '../types.ts'

// Selected values per enum column. An empty/absent set means "no filter on this column".
export type EnumFilters = Record<string, Set<string>>
// [min, max] per numeric column.
export type NumericFilters = Record<string, [number, number]>

const DIFFICULTY_ORDER = ['Easy', 'Medium', 'Hard']

// Distinct values per enum column, computed server-side-style from the data itself —
// the user never types a value, so nothing they enter reaches a query (same trust model
// as the old Streamlit demo, now entirely client-side).
export function buildFacets(designs: Design[]): Record<string, string[]> {
  const sets: Record<string, Set<string>> = {}
  for (const col of ENUM_COLUMNS) sets[col.key] = new Set()
  for (const d of designs) {
    for (const col of ENUM_COLUMNS) {
      const v = d[col.key]
      if (v != null) sets[col.key].add(String(v))
    }
  }
  const facets: Record<string, string[]> = {}
  for (const key of Object.keys(sets)) {
    const values = [...sets[key]]
    facets[key] =
      key === 'difficulty'
        ? values.sort((a, b) => DIFFICULTY_ORDER.indexOf(a) - DIFFICULTY_ORDER.indexOf(b))
        : values.sort((a, b) => a.localeCompare(b))
  }
  return facets
}

// [min, max] per numeric column, from the data.
export function numericBounds(designs: Design[]): NumericFilters {
  const bounds: NumericFilters = {}
  for (const col of NUMERIC_COLUMNS) bounds[col.key] = [Infinity, -Infinity]
  for (const d of designs) {
    for (const col of NUMERIC_COLUMNS) {
      const v = d[col.key] as number
      const b = bounds[col.key]
      if (v < b[0]) b[0] = v
      if (v > b[1]) b[1] = v
    }
  }
  for (const col of NUMERIC_COLUMNS) {
    if (!Number.isFinite(bounds[col.key][0])) bounds[col.key] = [0, 1]
  }
  return bounds
}

export function applyFilters(
  designs: Design[],
  enumFilters: EnumFilters,
  numericFilters: NumericFilters,
): Design[] {
  return designs.filter((d) => {
    for (const col of ENUM_COLUMNS) {
      const sel = enumFilters[col.key]
      if (sel && sel.size > 0 && !sel.has(String(d[col.key]))) return false
    }
    for (const col of NUMERIC_COLUMNS) {
      const r = numericFilters[col.key]
      if (r) {
        const v = d[col.key] as number
        if (v < r[0] || v > r[1]) return false
      }
    }
    return true
  })
}

export function sortDesigns(
  designs: Design[],
  key: keyof Design,
  dir: 'asc' | 'desc',
): Design[] {
  const sign = dir === 'asc' ? 1 : -1
  return [...designs].sort((a, b) => {
    const av = a[key]
    const bv = b[key]
    if (av === bv) return 0
    if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * sign
    return String(av).localeCompare(String(bv)) * sign
  })
}
