// Monaco ships with the app: loading it from a CDN would need a script-src
// exception in the Content-Security-Policy and run code we do not version.
//
// Workers come from Vite `?worker` imports, i.e. same-origin files (SEC-13).
// Without MonacoEnvironment.getWorker, Monaco starts its core editor worker
// from a blob: bootstrap that imports a tiny module with relative imports;
// Vite inlines that module as a data: URL, which neither resolves nor passes
// `script-src 'self'`. Once getWorker exists, Monaco uses it for every label
// (also the language workers), so it has to cover all of them. Workers load
// lazily, only when a model of that language is opened.
import type * as Monaco from 'monaco-editor'

type WorkerModule = { default: new () => Worker }
export type WorkerLoaders = Record<string, () => Promise<WorkerModule>>

const editorWorker = () => import('monaco-editor/editor/editor.worker?worker')
const htmlWorker = () => import('monaco-editor/language/html/html.worker?worker')
const cssWorker = () => import('monaco-editor/language/css/css.worker?worker')
const jsonWorker = () => import('monaco-editor/language/json/json.worker?worker')
const tsWorker = () => import('monaco-editor/language/typescript/ts.worker?worker')

export const EDITOR_WORKER_LABEL = 'editorWorkerService'

export const WORKER_LOADERS: WorkerLoaders = {
  [EDITOR_WORKER_LABEL]: editorWorker,
  html: htmlWorker,
  handlebars: htmlWorker,
  razor: htmlWorker,
  css: cssWorker,
  scss: cssWorker,
  less: cssWorker,
  json: jsonWorker,
  typescript: tsWorker,
  javascript: tsWorker,
}

export function monacoEnvironment(loaders: WorkerLoaders = WORKER_LOADERS): Monaco.Environment {
  return {
    getWorker(_workerId: string, label: string) {
      const load = loaders[label] ?? loaders[EDITOR_WORKER_LABEL]!
      return load().then(module => new module.default())
    },
  }
}

let pending: Promise<typeof Monaco> | null = null

export function loadMonaco(): Promise<typeof Monaco> {
  pending ??= import('monaco-editor').then(monaco => {
    globalThis.MonacoEnvironment = monacoEnvironment()
    return monaco
  })
  return pending
}
