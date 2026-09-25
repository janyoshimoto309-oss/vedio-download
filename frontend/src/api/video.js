async function parseError(res) {
  let detail = `请求失败 (${res.status})`
  try {
    const data = await res.json()
    if (typeof data.detail === 'string') detail = data.detail
    else if (Array.isArray(data.detail)) detail = data.detail.map((d) => d.msg || d).join('; ')
  } catch {
    /* ignore */
  }
  throw new Error(detail)
}

export async function fetchHealth() {
  const res = await fetch('/api/health')
  if (!res.ok) await parseError(res)
  return res.json()
}

export async function fetchVideoInfo(url) {
  const res = await fetch('/api/video/info', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
  if (!res.ok) await parseError(res)
  return res.json()
}

export async function downloadVideo(payload) {
  const res = await fetch('/api/video/download', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) await parseError(res)
  return res.json()
}
