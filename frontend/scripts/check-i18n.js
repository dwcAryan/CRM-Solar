import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const localesDir = path.resolve(__dirname, '../src/locales')

const enDir = path.join(localesDir, 'en')
const hiDir = path.join(localesDir, 'hi')

if (!fs.existsSync(enDir) || !fs.existsSync(hiDir)) {
  console.error('[i18n-check] Missing en or hi directory!')
  process.exit(1)
}

const enFiles = fs.readdirSync(enDir).filter((f) => f.endsWith('.json'))
let hasError = false
let totalKeys = 0

function getAllKeys(obj, prefix = '') {
  let keys = []
  for (const k of Object.keys(obj)) {
    const fullKey = prefix ? `${prefix}.${k}` : k
    if (typeof obj[k] === 'object' && obj[k] !== null && !Array.isArray(obj[k])) {
      keys = keys.concat(getAllKeys(obj[k], fullKey))
    } else {
      keys.push(fullKey)
    }
  }
  return keys
}

for (const file of enFiles) {
  const enPath = path.join(enDir, file)
  const hiPath = path.join(hiDir, file)

  if (!fs.existsSync(hiPath)) {
    console.warn(`[i18n-check] Warning: ${file} exists in en but missing in hi`)
    continue
  }

  const enJson = JSON.parse(fs.readFileSync(enPath, 'utf8'))
  const hiJson = JSON.parse(fs.readFileSync(hiPath, 'utf8'))

  const enKeys = getAllKeys(enJson)
  const hiKeys = new Set(getAllKeys(hiJson))
  totalKeys += enKeys.length

  const missingInHi = enKeys.filter((k) => !hiKeys.has(k))
  if (missingInHi.length > 0) {
    console.warn(`[i18n-check] ${file}: ${missingInHi.length} keys in en missing in hi: ${missingInHi.slice(0, 5).join(', ')}...`)
  }
}

console.log(`[i18n-check] Checked ${enFiles.length} namespaces with ${totalKeys} keys across locales. Key parity check completed.`)
