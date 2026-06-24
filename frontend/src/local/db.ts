import Database from '@tauri-apps/plugin-sql'

let dbPromise: Promise<Database> | null = null

function localDbErrorMessage(error: unknown) {
  if (error instanceof Error) return error.message
  if (typeof error === 'string') return error
  try {
    return JSON.stringify(error)
  } catch {
    return String(error)
  }
}

export function isDesktopRuntime() {
  return Boolean((window as unknown as { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__)
}

export async function getLocalDb() {
  if (!isDesktopRuntime()) {
    throw new Error('本地题库需要在 Quiz Pass 桌面客户端中使用')
  }
  if (!dbPromise) {
    dbPromise = Database.load('sqlite:quiz-pass-local.db').then(async (db) => {
      await migrate(db)
      return db
    }).catch((error) => {
      dbPromise = null
      throw new Error(`本地数据库初始化失败：${localDbErrorMessage(error)}`)
    })
  }
  return dbPromise
}

async function migrate(db: Database) {
  await db.execute('PRAGMA foreign_keys = ON')
  await db.execute(`
    CREATE TABLE IF NOT EXISTS client_meta (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    )
  `)
  await db.execute(`
    CREATE TABLE IF NOT EXISTS sync_state (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
  `)
  await db.execute(`
    CREATE TABLE IF NOT EXISTS sync_queue (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      target_type TEXT NOT NULL,
      target_id INTEGER NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending',
      error_message TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
  `)
  await db.execute(`
    CREATE TABLE IF NOT EXISTS local_banks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      remote_bank_id INTEGER NOT NULL UNIQUE,
      title TEXT NOT NULL,
      description TEXT,
      owner_json TEXT NOT NULL,
      tags_json TEXT NOT NULL,
      content_hash TEXT NOT NULL,
      question_count INTEGER NOT NULL DEFAULT 0,
      downloaded_at TEXT NOT NULL,
      remote_updated_at TEXT NOT NULL
    )
  `)
  await db.execute(`
    CREATE TABLE IF NOT EXISTS local_questions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      local_bank_id INTEGER NOT NULL,
      remote_question_id INTEGER NOT NULL,
      type TEXT NOT NULL,
      stem TEXT NOT NULL,
      explanation TEXT,
      difficulty TEXT,
      source TEXT,
      generated_model TEXT,
      sort_order INTEGER NOT NULL DEFAULT 0,
      is_active INTEGER NOT NULL DEFAULT 1,
      UNIQUE(local_bank_id, remote_question_id),
      FOREIGN KEY(local_bank_id) REFERENCES local_banks(id) ON DELETE CASCADE
    )
  `)
  await ensureColumn(db, 'local_questions', 'is_active', 'INTEGER NOT NULL DEFAULT 1')
  await db.execute(`
    CREATE TABLE IF NOT EXISTS local_options (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      local_question_id INTEGER NOT NULL,
      remote_option_id INTEGER NOT NULL,
      label TEXT NOT NULL,
      content TEXT NOT NULL,
      is_correct INTEGER NOT NULL DEFAULT 0,
      sort_order INTEGER NOT NULL DEFAULT 0,
      FOREIGN KEY(local_question_id) REFERENCES local_questions(id) ON DELETE CASCADE
    )
  `)
  await db.execute(`
    CREATE TABLE IF NOT EXISTS local_blanks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      local_question_id INTEGER NOT NULL,
      remote_blank_id INTEGER NOT NULL,
      label TEXT NOT NULL,
      answers_json TEXT NOT NULL,
      sort_order INTEGER NOT NULL DEFAULT 0,
      FOREIGN KEY(local_question_id) REFERENCES local_questions(id) ON DELETE CASCADE
    )
  `)
  await db.execute(`
    CREATE TABLE IF NOT EXISTS local_practice_sessions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      client_session_id TEXT NOT NULL UNIQUE,
      local_bank_id INTEGER NOT NULL,
      remote_bank_id INTEGER NOT NULL,
      mode TEXT NOT NULL,
      status TEXT NOT NULL,
      total_questions INTEGER NOT NULL DEFAULT 0,
      correct_count INTEGER NOT NULL DEFAULT 0,
      score REAL NOT NULL DEFAULT 0,
      started_at TEXT NOT NULL,
      submitted_at TEXT,
      sync_status TEXT NOT NULL DEFAULT 'pending',
      sync_error TEXT,
      remote_session_id INTEGER,
      synced_at TEXT,
      FOREIGN KEY(local_bank_id) REFERENCES local_banks(id) ON DELETE CASCADE
    )
  `)
  await db.execute(`
    CREATE TABLE IF NOT EXISTS local_session_questions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      session_id INTEGER NOT NULL,
      local_question_id INTEGER NOT NULL,
      sort_order INTEGER NOT NULL DEFAULT 0,
      UNIQUE(session_id, local_question_id),
      FOREIGN KEY(session_id) REFERENCES local_practice_sessions(id) ON DELETE CASCADE,
      FOREIGN KEY(local_question_id) REFERENCES local_questions(id) ON DELETE CASCADE
    )
  `)
  await db.execute(`
    CREATE TABLE IF NOT EXISTS local_answers (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      session_id INTEGER NOT NULL,
      local_question_id INTEGER NOT NULL,
      selected_option_ids_json TEXT NOT NULL,
      text_answers_json TEXT NOT NULL,
      is_correct INTEGER NOT NULL DEFAULT 0,
      is_submitted INTEGER NOT NULL DEFAULT 0,
      answered_at TEXT NOT NULL,
      UNIQUE(session_id, local_question_id),
      FOREIGN KEY(session_id) REFERENCES local_practice_sessions(id) ON DELETE CASCADE,
      FOREIGN KEY(local_question_id) REFERENCES local_questions(id) ON DELETE CASCADE
    )
  `)
  await db.execute(`
    CREATE TABLE IF NOT EXISTS local_mistake_attempts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      session_id INTEGER NOT NULL,
      local_bank_id INTEGER NOT NULL,
      local_question_id INTEGER NOT NULL,
      question_snapshot_json TEXT NOT NULL,
      user_answer_json TEXT NOT NULL,
      is_resolved INTEGER NOT NULL DEFAULT 0,
      wrong_at TEXT NOT NULL,
      resolved_at TEXT,
      FOREIGN KEY(session_id) REFERENCES local_practice_sessions(id) ON DELETE CASCADE,
      FOREIGN KEY(local_bank_id) REFERENCES local_banks(id) ON DELETE CASCADE,
      FOREIGN KEY(local_question_id) REFERENCES local_questions(id) ON DELETE CASCADE
    )
  `)
}

async function ensureColumn(db: Database, table: string, column: string, definition: string) {
  const columns = await db.select<Array<{ name: string }>>(`PRAGMA table_info(${table})`)
  if (!columns.some((item) => item.name === column)) {
    await db.execute(`ALTER TABLE ${table} ADD COLUMN ${column} ${definition}`)
  }
}
