import type { BankPracticeProgress, PracticeSession } from '../api/types'

type ProgressLike = Pick<
  BankPracticeProgress | PracticeSession,
  'status' | 'total_questions' | 'answered_count' | 'correct_count' | 'score' | 'started_at' | 'submitted_at' | 'last_answered_at'
>

function scoreText(score: number) {
  return Number.isInteger(score) ? String(score) : score.toFixed(1).replace(/\.0$/, '')
}

export function practiceProgressPercent(session: ProgressLike | null | undefined) {
  if (!session) return 0
  if (session.status === 'submitted') return Math.max(0, Math.min(100, Math.round(session.score || 0)))
  if (!session.total_questions) return 0
  return Math.max(0, Math.min(100, Math.round((session.answered_count / session.total_questions) * 100)))
}

export function practiceProgressText(session: ProgressLike | null | undefined) {
  if (!session) return ''
  if (session.status === 'submitted') {
    return `${scoreText(session.score || 0)}分 · 正确 ${session.correct_count}/${session.total_questions}`
  }
  return `已做 ${session.answered_count}/${session.total_questions}`
}

export function practiceProgressColor(session: ProgressLike | null | undefined) {
  if (!session) return '#cbd5e1'
  if (session.status !== 'submitted') return '#818cf8'
  const score = session.score || 0
  if (score >= 80) return '#22c55e'
  if (score >= 60) return '#f59e0b'
  return '#f87171'
}

export function practiceProgressType(session: ProgressLike | null | undefined) {
  if (!session) return '进行中'
  return session.status === 'submitted' ? '上次成绩' : '进行中'
}

export function practiceLastActivity(session: ProgressLike | null | undefined) {
  return session?.last_answered_at || session?.submitted_at || session?.started_at || null
}

