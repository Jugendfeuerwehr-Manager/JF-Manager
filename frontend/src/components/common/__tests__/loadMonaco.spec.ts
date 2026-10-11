import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { EDITOR_WORKER_LABEL, WORKER_LOADERS, monacoEnvironment, type WorkerLoaders } from '../loadMonaco'

class EditorWorker {}
class HtmlWorker {}

const loaders: WorkerLoaders = {
  [EDITOR_WORKER_LABEL]: async () => ({ default: EditorWorker as unknown as new () => Worker }),
  html: async () => ({ default: HtmlWorker as unknown as new () => Worker }),
}

describe('Monaco workers (SEC-13)', () => {
  it('starts the editor worker from the bundled ?worker constructor, without blob: or data: URLs', async () => {
    const env = monacoEnvironment(loaders)
    await expect(env.getWorker!('workerMain.js', EDITOR_WORKER_LABEL)).resolves.toBeInstanceOf(EditorWorker)
    expect(env.getWorkerUrl).toBeUndefined()
  })

  it('serves language workers itself, because Monaco then asks getWorker for every label', async () => {
    const env = monacoEnvironment(loaders)
    await expect(env.getWorker!('workerMain.js', 'html')).resolves.toBeInstanceOf(HtmlWorker)
    await expect(env.getWorker!('workerMain.js', 'unknown')).resolves.toBeInstanceOf(EditorWorker)
  })

  it('covers every language worker Monaco ships', () => {
    for (const label of ['html', 'handlebars', 'razor', 'css', 'scss', 'less', 'json', 'typescript', 'javascript']) {
      expect(WORKER_LOADERS[label]).toBeTypeOf('function')
    }
  })
})

describe('no runtime code from foreign CDNs (SEC-13)', () => {
  const CDN = /cdn\.jsdelivr\.net|unpkg\.com|cdnjs\.cloudflare\.com|fonts\.googleapis\.com|@monaco-editor\/loader/

  function sources(dir: string): string[] {
    return readdirSync(dir).flatMap(name => {
      const path = join(dir, name)
      if (statSync(path).isDirectory()) return name === '__tests__' ? [] : sources(path)
      return /\.(ts|vue|css|html)$/.test(name) ? [path] : []
    })
  }

  it('application sources and index.html reference no CDN', () => {
    const root = resolve(__dirname, '../../../..')
    const offenders = [...sources(join(root, 'src')), join(root, 'index.html')]
      .filter(path => CDN.test(readFileSync(path, 'utf8')))
    expect(offenders).toEqual([])
  })
})
