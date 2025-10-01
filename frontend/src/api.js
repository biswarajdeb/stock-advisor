const API_BASE = import.meta.env.VITE_API_BASE || 'https://stock-advisor-2zca.onrender.com'

export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`)
  if (!res.ok) throw new Error('Health check failed')
  return res.json()
}

export async function getTopRecommendations(n = 3, page = 1, cap = 'all') {
  const url = new URL(`${API_BASE}/recommendations/top`)
  url.searchParams.set('n', n)
  url.searchParams.set('page', page)
  url.searchParams.set('cap', cap)
  const res = await fetch(url)
  if (!res.ok) throw new Error('Failed to fetch recommendations')
  return res.json()
}
