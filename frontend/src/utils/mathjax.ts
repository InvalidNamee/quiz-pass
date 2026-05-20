let mathJaxReady: Promise<unknown> | null = null

declare global {
  interface Window {
    MathJax?: {
      tex?: unknown
      options?: unknown
      startup?: { promise?: Promise<unknown> }
      texReset?: () => void
      tex2chtmlPromise?: (math: string, options?: { display?: boolean }) => Promise<HTMLElement>
      typesetPromise?: (elements: HTMLElement[]) => Promise<void>
      typesetClear?: (elements: HTMLElement[]) => void
    }
  }
}

function ensureMathJax() {
  if (!mathJaxReady) {
    window.MathJax = {
      tex: {
        inlineMath: [['\\(', '\\)']],
        displayMath: [['$$', '$$'], ['\\[', '\\]']],
        processEscapes: true,
      },
      options: {
        enableMenu: false,
      },
    }
    mathJaxReady = import('mathjax/tex-chtml.js').then(async () => {
      await Promise.race([
        window.MathJax?.startup?.promise ?? Promise.resolve(),
        new Promise((resolve) => setTimeout(resolve, 1500)),
      ])
    })
  }
  return mathJaxReady
}

export async function typesetMath(element: HTMLElement) {
  await ensureMathJax()
  if (!window.MathJax?.typesetPromise) return
  window.MathJax.typesetClear?.([element])
  window.MathJax.texReset?.()
  await window.MathJax.typesetPromise([element])
}

type MathToken = { type: 'text'; value: string } | { type: 'math'; value: string; display: boolean }

function findNextDelimiter(text: string, start: number) {
  const candidates = [
    { open: '\\(', close: '\\)', display: false },
    { open: '\\[', close: '\\]', display: true },
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
    tokens.push({ type: 'math', value: text.slice(contentStart, contentEnd), display: delimiter.display })
    cursor = contentEnd + delimiter.close.length
  }
  return tokens
}

export async function renderMathText(element: HTMLElement, text: string) {
  element.textContent = text
  await ensureMathJax()
  window.MathJax?.typesetClear?.([element])
  const renderer = window.MathJax?.tex2chtmlPromise
  if (!renderer) {
    await window.MathJax?.typesetPromise?.([element])
    return
  }
  const tokens = tokenizeMathText(text)
  const fragment = document.createDocumentFragment()
  for (const token of tokens) {
    if (token.type === 'text') {
      fragment.appendChild(document.createTextNode(token.value))
    } else {
      try {
        const node = await renderer(token.value, { display: token.display })
        fragment.appendChild(node)
      } catch {
        fragment.appendChild(document.createTextNode(token.display ? `\\[${token.value}\\]` : `\\(${token.value}\\)`))
      }
    }
  }
  element.replaceChildren(fragment)
}
