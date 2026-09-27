<script setup>
import { computed, defineAsyncComponent, onMounted, ref, watch } from 'vue'
import { fetchNotesReady, summarizePart } from '../api/notes'

const MindMapCanvas = defineAsyncComponent(() => import('./MindMapCanvas.vue'))

const props = defineProps({
  url: { type: String, required: true },
  embedded: { type: Boolean, default: false },
  inset: { type: Boolean, default: false },
})

const llmReady = ref(true)
const error = ref('')
const meta = ref(null)
const outline = ref(null)
const keyPoints = ref(null)
const mindMap = ref(null)
const transcript = ref(null)
const markdownParts = ref({})
const loadingPart = ref('')
const tab = ref('')
const copied = ref(false)
const mapCanvasRef = ref(null)
const exportingMap = ref(false)

const PARTS = [
  { id: 'outline', label: '大纲', needsKey: true },
  { id: 'points', label: '要点', needsKey: true },
  { id: 'map', label: '脑图', needsKey: true },
  { id: 'transcript', label: '字幕', needsKey: false },
]

function hasPart(id) {
  if (id === 'outline') return outline.value != null
  if (id === 'points') return keyPoints.value != null
  if (id === 'map') return mindMap.value != null
  if (id === 'transcript') return transcript.value != null
  return false
}

watch(
  () => props.url,
  () => {
    error.value = ''
    meta.value = null
    outline.value = null
    keyPoints.value = null
    mindMap.value = null
    transcript.value = null
    markdownParts.value = {}
    loadingPart.value = ''
    tab.value = ''
    exportingMap.value = false
  },
)

onMounted(async () => {
  try {
    const ready = await fetchNotesReady()
    llmReady.value = Boolean(ready.llm)
  } catch {
    llmReady.value = false
  }
})

const visibleTabs = computed(() => PARTS.filter((item) => hasPart(item.id)))

const combinedMarkdown = computed(() => {
  const order = ['outline', 'points', 'map', 'transcript']
  const chunks = order.map((id) => markdownParts.value[id]).filter(Boolean)
  return chunks.join('\n')
})

function applyResult(part, data) {
  meta.value = {
    title: data.title,
    language: data.language,
    source: data.source,
  }
  markdownParts.value = { ...markdownParts.value, [part]: data.markdown }
  if (part === 'outline') outline.value = data.outline || []
  if (part === 'points') keyPoints.value = data.key_points || []
  if (part === 'map') mindMap.value = data.mind_map || { label: '视频内容', children: [] }
  if (part === 'transcript') transcript.value = data.transcript || []
  tab.value = part
}

async function generate(part) {
  error.value = ''
  loadingPart.value = part
  try {
    const data = await summarizePart(props.url, part)
    applyResult(part, data)
  } catch (e) {
    error.value = e.message || '生成失败'
  } finally {
    loadingPart.value = ''
  }
}

function partBusy() {
  return Boolean(loadingPart.value)
}

function partLabel(item) {
  if (loadingPart.value === item.id) return '正在生成…'
  if (item.id === 'outline' && outline.value) return '重新生成大纲'
  if (item.id === 'points' && keyPoints.value) return '重新生成要点'
  if (item.id === 'map' && mindMap.value) return '重新生成脑图'
  if (item.id === 'transcript' && transcript.value) return '重新获取字幕'
  return `生成${item.label}`
}

function safeName() {
  const raw = (meta.value?.title || '学习笔记').replace(/[\\/:*?"<>|]/g, '').slice(0, 80)
  return raw || '学习笔记'
}

function downloadBlob(filename, mime, content) {
  const blob = new Blob([content], { type: mime })
  const href = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = href
  a.download = filename
  a.click()
  URL.revokeObjectURL(href)
}

async function copyMarkdown() {
  if (!combinedMarkdown.value) return
  try {
    await navigator.clipboard.writeText(combinedMarkdown.value)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 1600)
  } catch {
    error.value = '复制失败，请改用导出文件。'
  }
}

function exportMarkdown() {
  if (!combinedMarkdown.value) return
  downloadBlob(`${safeName()}.md`, 'text/markdown;charset=utf-8', combinedMarkdown.value)
}

async function exportMindPng() {
  if (!mapCanvasRef.value || exportingMap.value) return
  exportingMap.value = true
  error.value = ''
  try {
    await mapCanvasRef.value.exportPng(`${safeName()}-脑图`)
  } catch (e) {
    error.value = e.message || '导出图片失败'
  } finally {
    exportingMap.value = false
  }
}

function exportDoc() {
  if (!combinedMarkdown.value) return
  const escape = (s) =>
    String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${escape(meta.value?.title)}</title></head><body>
<pre style="white-space:pre-wrap;font-family:system-ui,sans-serif;font-size:14px">${escape(combinedMarkdown.value)}</pre>
</body></html>`
  downloadBlob(`${safeName()}.doc`, 'application/msword;charset=utf-8', html)
}
</script>

<template>
  <section
    class="w-full"
    :class="
      inset
        ? ''
        : embedded
          ? 'rounded-2xl border border-line bg-raised'
          : 'mx-auto mt-4 max-w-search rounded-2xl border border-line bg-raised'
    "
  >
    <div class="p-5 text-left" :class="inset ? 'pb-4' : ''">
      <p v-if="!inset" class="text-sm font-semibold text-ink">AI 学习笔记</p>
      <p class="text-xs leading-relaxed text-muted" :class="inset ? '' : 'mt-1'">
        选一项生成；生成后可切换查看。
      </p>
      <p v-if="!llmReady" class="mt-1 text-xs text-warn">
        大纲、要点和脑图暂时不可用。字幕还可以看。
      </p>
      <div class="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <button
          v-for="item in PARTS"
          :key="item.id"
          type="button"
          :disabled="partBusy() || !url || (item.needsKey && !llmReady)"
          class="h-9 rounded-lg bg-accent-soft px-2.5 text-[13px] font-semibold text-accent transition hover:bg-accent/10 disabled:opacity-70"
          @click="generate(item.id)"
        >
          {{ partLabel(item) }}
        </button>
      </div>
    </div>

    <p v-if="error" class="px-5 pb-4 text-left text-sm text-danger">{{ error }}</p>

    <div v-if="loadingPart" class="space-y-2 px-5 pb-5">
      <div class="h-3 w-2/3 animate-pulse rounded bg-skeleton" />
      <div class="h-3 w-full animate-pulse rounded bg-skeleton" />
      <div class="h-3 w-5/6 animate-pulse rounded bg-skeleton" />
    </div>

    <div v-if="visibleTabs.length" class="border-t border-line px-5 pb-5 pt-4 text-left">
      <div class="flex flex-wrap gap-2">
        <button
          v-for="item in visibleTabs"
          :key="item.id"
          type="button"
          class="rounded-full px-3 py-1 text-xs font-medium"
          :class="tab === item.id ? 'bg-accent text-white' : 'bg-accent-soft text-accent'"
          @click="tab = item.id"
        >
          {{ item.label }}
        </button>
      </div>

      <div v-if="tab === 'outline'" class="mt-4 space-y-3">
        <article v-for="(item, i) in outline" :key="i" class="rounded-xl bg-surface px-3.5 py-3">
          <p class="text-xs text-muted">{{ item.timestamp }}</p>
          <h3 class="mt-0.5 text-sm font-semibold text-ink">{{ item.title }}</h3>
          <p v-if="item.summary" class="mt-1 text-[13px] leading-relaxed text-muted">{{ item.summary }}</p>
        </article>
        <p v-if="!outline.length" class="text-sm text-muted">这次没有整理出章节。</p>
      </div>

      <ol v-else-if="tab === 'points'" class="mt-4 list-decimal space-y-2 pl-5 text-[13px] leading-relaxed text-ink">
        <li v-for="(p, i) in keyPoints" :key="i">{{ p }}</li>
      </ol>

      <div v-else-if="tab === 'map'" class="mt-4">
        <MindMapCanvas
          v-if="mindMap"
          ref="mapCanvasRef"
          :node="mindMap"
          @error="error = $event"
        />
      </div>

      <div v-else-if="tab === 'transcript'" class="mt-4 max-h-72 overflow-auto rounded-xl bg-surface px-3 py-3">
        <p v-for="(cue, i) in transcript" :key="i" class="mb-2 text-[13px] leading-relaxed">
          <span class="mr-2 font-mono text-xs text-accent">{{ cue.timestamp }}</span>
          <span class="text-ink">{{ cue.text }}</span>
        </p>
      </div>

      <div v-if="combinedMarkdown" class="mt-4 flex flex-wrap gap-2">
        <button
          v-if="tab === 'map'"
          type="button"
          :disabled="exportingMap || !mapCanvasRef"
          class="rounded-lg border border-line px-3 py-2 text-xs font-medium text-ink hover:bg-surface disabled:opacity-70"
          @click="exportMindPng"
        >
          {{ exportingMap ? '正在导出…' : '导出图片' }}
        </button>
        <button
          type="button"
          class="rounded-lg border border-line px-3 py-2 text-xs font-medium text-ink hover:bg-surface"
          @click="copyMarkdown"
        >
          {{ copied ? '已复制' : '复制' }}
        </button>
        <button
          type="button"
          class="rounded-lg border border-line px-3 py-2 text-xs font-medium text-ink hover:bg-surface"
          @click="exportMarkdown"
        >
          导出 Markdown
        </button>
        <button
          v-if="tab !== 'map'"
          type="button"
          class="rounded-lg border border-line px-3 py-2 text-xs font-medium text-ink hover:bg-surface"
          @click="exportDoc"
        >
          导出 Word
        </button>
      </div>
    </div>
  </section>
</template>
