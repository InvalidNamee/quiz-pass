const { spawnSync } = require('node:child_process')
const path = require('node:path')

const command = process.argv[2] || 'build'
const extraArgs = process.argv.slice(3)

function hasCommand(name) {
  const result = spawnSync(name, ['--version'], { stdio: 'ignore', env: process.env })
  return result.status === 0
}

function cargoDirFromRustup() {
  const result = spawnSync('rustup', ['which', 'cargo'], {
    encoding: 'utf8',
    env: process.env,
  })
  if (result.status !== 0) return null
  const cargoPath = result.stdout.trim()
  return cargoPath ? path.dirname(cargoPath) : null
}

const env = { ...process.env }
if (!hasCommand('cargo')) {
  const cargoDir = cargoDirFromRustup()
  if (cargoDir) {
    env.PATH = `${cargoDir}${path.delimiter}${env.PATH || ''}`
  }
}

const result = spawnSync('tauri', [command, ...extraArgs], {
  stdio: 'inherit',
  env,
  shell: process.platform === 'win32',
})

process.exit(result.status ?? 1)
