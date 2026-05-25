import katex from 'katex'

type MathToken = { type: 'text'; value: string } | { type: 'math'; value: string; display: boolean; raw: string }

function escapeHtml(value: string) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

function renderTextWithBlankPlaceholders(value: string) {
  return escapeHtml(value).replace(/\{\{([^{}]+)\}\}/g, (_match, label: string) => {
    const safeLabel = escapeHtml(String(label).trim())
    return `<span style="display:inline-flex;align-items:center;min-width:4.5em;height:1.7em;margin:0 0.2em;padding:0 0.75em;border:1px solid #cbd5e1;border-bottom-color:#64748b;border-radius:999px;background:#f8fafc;color:#64748b;font-size:0.9em;font-weight:700;vertical-align:baseline;">空 ${safeLabel}</span>`
  })
}

function findNextDelimiter(text: string, start: number) {
  const candidates = [
    { open: '\\(', close: '\\)', display: false },
    { open: '\\[', close: '\\]', display: true },
    { open: '$', close: '$', display: false },
    { open: '$$', close: '$$', display: true },
  ]
    .map((delimiter) => ({ ...delimiter, index: text.indexOf(delimiter.open, start) }))
    .filter((item) => item.index >= 0)
    .sort((a, b) => a.index - b.index)
  return candidates[0]
}

function tokenizeMathText(text: string): MathToken[] {
  const tokens: MathToken[] = []
  let cursor = 0
  while (cursor < text.length) {
    const delimiter = findNextDelimiter(text, cursor)
    if (!delimiter) {
      tokens.push({ type: 'text', value: text.slice(cursor) })
      break
    }
    if (delimiter.index > cursor) tokens.push({ type: 'text', value: text.slice(cursor, delimiter.index) })
    const contentStart = delimiter.index + delimiter.open.length
    const contentEnd = text.indexOf(delimiter.close, contentStart)
    if (contentEnd < 0) {
      tokens.push({ type: 'text', value: text.slice(delimiter.index) })
      break
    }
    tokens.push({
      type: 'math',
      value: text.slice(contentStart, contentEnd),
      display: delimiter.display,
      raw: text.slice(delimiter.index, contentEnd + delimiter.close.length),
    })
    cursor = contentEnd + delimiter.close.length
  }
  return tokens
}

export function renderMathTextToHtml(text: string) {
  return tokenizeMathText(text).map((token) => {
    if (token.type === 'text') return renderTextWithBlankPlaceholders(token.value)
    try {
      return katex.renderToString(token.value, {
        displayMode: token.display,
        throwOnError: false,
        strict: 'ignore',
        trust: false,
      })
    } catch {
      return escapeHtml(token.raw)
    }
  }).join('')
}
