import React, { useEffect, useState, useCallback } from 'react'
import { getTopRecommendations, getHealth } from './api'

export default function App() {
  const [health, setHealth] = useState(null)
  const [recs, setRecs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(1) // 1..3
  const [cap, setCap] = useState('all') // 'all' | 'small' | 'mid' | 'large'
  const [hasMore, setHasMore] = useState(true)

  const loadPage = useCallback(async (pageToLoad, capVal) => {
    const data = await getTopRecommendations(3, pageToLoad, capVal)
    const items = data.recommendations || []
    // merge unique by ticker
    setRecs(prev => {
      const existing = new Set(prev.map(x => x.ticker))
      const merged = [...prev]
      for (const it of items) {
        if (!existing.has(it.ticker)) merged.push(it)
      }
      return merged
    })
    // allow up to 3 pages regardless of backend totals for demo pagination
    setHasMore(pageToLoad < 3)
  }, [])

  useEffect(() => {
    async function init() {
      try {
        const h = await getHealth()
        setHealth(h)
        setLoading(true)
        setRecs([])
        setPage(1)
        await loadPage(1, cap)
      } catch (e) {
        setError(e.message || 'Failed to load')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [cap, loadPage])

  const onNext3 = async () => {
    const next = page + 1
    if (next > 3 || !hasMore) return
    setLoading(true)
    try {
      await loadPage(next, cap)
      setPage(next)
    } catch (e) {
      setError(e.message || 'Failed to load more')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <div className="header">
        <h1 className="title">Stock Advisor (Free)</h1>
        <span className="subtle">Demo: Next 3 (up to 9) + Cap filter</span>
      </div>

      <section style={{ marginTop: 12 }}>
        <h3>Backend Health</h3>
        <pre className="card" style={{ overflowX: 'auto' }}>
{JSON.stringify(health, null, 2)}
        </pre>
      </section>

      <section style={{ marginTop: 12 }}>
        <div className="toolbar">
          <label htmlFor="cap">Market Cap:</label>
          <select id="cap" value={cap} onChange={(e) => setCap(e.target.value)} disabled={loading}>
            <option value="all">All</option>
            <option value="large">Large Cap</option>
            <option value="mid">Mid Cap</option>
            <option value="small">Small Cap</option>
          </select>
          <span className="page">Page {page}/3</span>
          <button onClick={async () => { if (page>1){ setLoading(true); try{ setPage(p=>p-1); setRecs([]); await loadPage(page-1, cap); } finally { setLoading(false) } } }} disabled={page <= 1 || loading}>Previous</button>
          <button onClick={onNext3} disabled={page >= 3 || loading}>Next 3</button>
          <button onClick={async () => { setLoading(true); try{ setRecs([]); setPage(1); await loadPage(1, cap); } finally { setLoading(false) } }} disabled={loading}>Reset</button>
        </div>
        {loading && <p className="subtle">Loading...</p>}
        {error && <p style={{ color: 'tomato' }}>{error}</p>}
        {!loading && !error && recs.length === 0 && <p className="subtle">No recommendations available.</p>}
        <div className="grid">
          {recs.map((r) => (
            <div key={r.ticker} className="card">
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12 }}>
                <h4 style={{ margin: '4px 0' }}>{r.ticker}</h4>
                {r.cap && <span className="badge">{r.cap?.toUpperCase?.()}</span>}
              </div>
              <div className="kv">
                <span><b>Score:</b> {r.composite_score}</span>
                <span><b>Class:</b> {r.classification}</span>
                <span><b>Hold:</b> {r.holding_duration}</span>
                <span><b>Conf:</b> {r.confidence}</span>
              </div>
              <div className="hr" />
              <p style={{ marginTop: 8 }} className="subtle">{r.rationale}</p>
              <div className="kv">
                <div><b>Stop-loss:</b> {r.stop_loss?.toFixed?.(2) ?? r.stop_loss}</div>
                <div><b>Targets:</b> {Array.isArray(r.target_band) ? r.target_band.join(' , ') : ''}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <footer className="footer">
        Disclaimer: This output is informational only; not financial advice.
      </footer>
    </div>
  )
}
