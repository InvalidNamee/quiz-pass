import type { QuestionBankTag } from '../../api/types'

export type TagInputValue = QuestionBankTag | string | null | undefined

export function tagLabel(tag: TagInputValue) {
  if (typeof tag === 'string') return tag
  return tag?.name || ''
}

export function tagKey(tag: TagInputValue, index: number) {
  if (typeof tag === 'string') return tag || index
  return tag?.id || tag?.name || index
}

export function normalizeTagNames(values: TagInputValue[] = []) {
  const seen = new Set<string>()
  const names: string[] = []
  values.forEach((value) => {
    const rawName = tagLabel(value)
    const name = rawName.trim()
    const normalized = name.toLowerCase()
    if (!name || normalized === 'none' || seen.has(normalized)) return
    seen.add(normalized)
    names.push(name)
  })
  return names
}
