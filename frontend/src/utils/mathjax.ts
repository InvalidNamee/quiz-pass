let mathJaxReady: Promise<unknown> | null = null

declare global {
  interface Window {
    MathJax?: {
      tex?: unknown
      options?: unknown
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
    mathJaxReady = import('mathjax/tex-chtml.js')
  }
  return mathJaxReady
}

export async function typesetMath(element: HTMLElement) {
  await ensureMathJax()
  if (!window.MathJax?.typesetPromise) return
  window.MathJax.typesetClear?.([element])
  await window.MathJax.typesetPromise([element])
}
