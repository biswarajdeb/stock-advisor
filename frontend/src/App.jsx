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
    <div style={{ fontFamily: 'system-ui, Arial, sans-serif', padding: 16, maxWidth: 960, margin: '0 auto' }}>
      <h1>Stock Advisor (Free)</h1>
      <p style={{ color: '#555' }}>Demo MVP dashboard. Now supports Next 3 (up to 9) and market-cap filter.</p>

      <section style={{ marginTop: 16 }}>
        <h3>Backend Health</h3>
        <pre style={{ background:'#f5f5f5', padding: 12, borderRadius: 8 }}>
{JSON.stringify(health, null, 2)}
        </pre>
      </section>

      <section style={{ marginTop: 16 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap' }}>
          <h3 style={{ margin: 0 }}>Top Recommendations</h3>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <label htmlFor="cap">Market Cap:</label>
            <select id="cap" value={cap} onChange={(e) => setCap(e.target.value)}>
              <option value="all">All</option>
              <option value="large">Large Cap</option>
              <option value="mid">Mid Cap</option>
              <option value="small">Small Cap</option>
            </select>
            <button onClick={onNext3} disabled={page >= 3 || loading}>
              Next 3
            </button>
          </div>
        </div>
        {loading && <p>Loading...</p>}
        {error && <p style={{ color: 'tomato' }}>{error}</p>}
        {!loading && !error && recs.length === 0 && <p>No recommendations available.</p>}
        <div style={{ display: 'grid', gap: 12 }}>
          {recs.map((r) => (
            <div key={r.ticker} style={{ border: '1px solid #ddd', borderRadius: 8, padding: 12 }}>
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12 }}>
                <h4 style={{ margin: '4px 0' }}>{r.ticker}</h4>
                {r.cap && <span style={{ fontSize: 12, color: '#666' }}>{r.cap?.toUpperCase?.()}</span>}
              </div>
              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 14 }}>
                <span><b>Score:</b> {r.composite_score}</span>
                <span><b>Class:</b> {r.classification}</span>
                <span><b>Hold:</b> {r.holding_duration}</span>
                <span><b>Conf:</b> {r.confidence}</span>
              </div>
              <p style={{ marginTop: 8 }}>{r.rationale}</p>
              <div style={{ fontSize: 14 }}>
                <div><b>Stop-loss:</b> {r.stop_loss?.toFixed?.(2) ?? r.stop_loss}</div>
                <div><b>Targets:</b> {Array.isArray(r.target_band) ? r.target_band.join(' , ') : ''}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <footer style={{ marginTop: 24, fontSize: 12, color: '#777' }}>
        Disclaimer: This output is informational only; not financial advice.
      </footer>
    </div>
  )
}
