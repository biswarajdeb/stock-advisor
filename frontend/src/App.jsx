import React, { useEffect, useState } from 'react'
import { getTopRecommendations, getHealth } from './api'

export default function App() {
  const [health, setHealth] = useState(null)
  const [recs, setRecs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function load() {
      try {
        const h = await getHealth()
        setHealth(h)
        const data = await getTopRecommendations(3)
        setRecs(data.recommendations || [])
      } catch (e) {
        setError(e.message || 'Failed to load')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <div style={{ fontFamily: 'system-ui, Arial, sans-serif', padding: 16, maxWidth: 960, margin: '0 auto' }}>
      <h1>Stock Advisor (Free)</h1>
      <p style={{ color: '#555' }}>Demo MVP dashboard. Frontend ready for Netlify; backend FastAPI stub.</p>

      <section style={{ marginTop: 16 }}>
        <h3>Backend Health</h3>
        <pre style={{ background:'#f5f5f5', padding: 12, borderRadius: 8 }}>
{JSON.stringify(health, null, 2)}
        </pre>
      </section>

      <section style={{ marginTop: 16 }}>
        <h3>Top Recommendations</h3>
        {loading && <p>Loading...</p>}
        {error && <p style={{ color: 'tomato' }}>{error}</p>}
        {!loading && !error && recs.length === 0 && <p>No recommendations available.</p>}
        <div style={{ display: 'grid', gap: 12 }}>
          {recs.map((r) => (
            <div key={r.ticker} style={{ border: '1px solid #ddd', borderRadius: 8, padding: 12 }}>
              <h4 style={{ margin: '4px 0' }}>{r.ticker}</h4>
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
