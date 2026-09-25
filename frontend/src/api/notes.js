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

export async function fetchNotesReady() {
  const res = await fetch('/api/notes/ready')
  if (!res.ok) await parseError(res)
  return res.json()
}

export async function summarizeVideo(url) {
  const res = await fetch('/api/notes/summarize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
  if (!res.ok) await parseError(res)
  return res.json()
}
