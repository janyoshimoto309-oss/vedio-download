<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { fetchNotesReady, summarizeVideo } from '../api/notes'
import MindMapTree from './MindMapTree.vue'

const props = defineProps({
  url: { type: String, required: true },
})

const llmReady = ref(true)
const loading = ref(false)
const error = ref('')
const notes = ref(null)
const tab = ref('outline')
const copied = ref(false)

watch(
  () => props.url,
  () => {
    notes.value = null
    error.value = ''
    tab.value = 'outline'
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

const sourceLabel = computed(() => {
  if (!notes.value) return ''
  return notes.value.source === 'official' ? '官方字幕' : '自动字幕'
})

const tabs = [
  { id: 'outline', label: '大纲' },
  { id: 'points', label: '要点' },
  { id: 'map', label: '脑图' },
  { id: 'script', label: '字幕' },
]

async function generate() {
  error.value = ''
  loading.value = true
  try {
    notes.value = await summarizeVideo(props.url)
    tab.value = 'outline'
  } catch (e) {
    notes.value = null
    error.value = e.message || '生成失败'
  } finally {
    loading.value = false
  }
}

function safeName() {
  const raw = (notes.value?.title || '学习笔记').replace(/[\\/:*?"<>|]/g, '').slice(0, 80)
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
  if (!notes.value?.markdown) return
  try {
    await navigator.clipboard.writeText(notes.value.markdown)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 1600)
  } catch {
    error.value = '复制失败，请改用导出文件。'
  }
}

function exportMarkdown() {
  if (!notes.value?.markdown) return
  downloadBlob(`${safeName()}.md`, 'text/markdown;charset=utf-8', notes.value.markdown)
}

function exportDoc() {
  if (!notes.value) return
  const escape = (s) =>
    String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${escape(notes.value.title)}</title></head><body>
<pre style="white-space:pre-wrap;font-family:system-ui,sans-serif;font-size:14px">${escape(notes.value.markdown)}</pre>
</body></html>`
  downloadBlob(`${safeName()}.doc`, 'application/msword;charset=utf-8', html)
}
</script>

<template>
  <section class="mx-auto mt-4 w-full max-w-search rounded-2xl border border-line bg-raised">
    <div class="flex flex-col gap-3 p-5 md:flex-row md:items-center md:justify-between">
      <div class="min-w-0 text-left">
        <p class="text-sm font-semibold text-ink">AI 学习笔记</p>
        <p class="mt-1 text-xs leading-relaxed text-muted">
          用字幕生成大纲、要点、脑图和原文。不必先下载整片。油管带 CC / 自动字幕最稳；B 站弹幕和烧在画面上的字不算字幕轨。
        </p>
        <p v-if="!llmReady" class="mt-1 text-xs text-warn">
          后端尚未读到 DeepSeek Key。在 backend/.env 填写 DEEPSEEK_API_KEY 后重启 uvicorn。
        </p>
      </div>
      <button
        type="button"
        :disabled="loading || !url"
        class="h-10 shrink-0 rounded-xl bg-accent px-4 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-70"
        @click="generate"
      >
        {{ loading ? '正在生成…' : notes ? '重新生成' : '生成学习笔记' }}
      </button>
    </div>

    <p v-if="error" class="px-5 pb-4 text-left text-sm text-danger">{{ error }}</p>

    <div v-if="loading" class="space-y-2 px-5 pb-5">
      <div class="h-3 w-2/3 animate-pulse rounded bg-skeleton" />
      <div class="h-3 w-full animate-pulse rounded bg-skeleton" />
      <div class="h-3 w-5/6 animate-pulse rounded bg-skeleton" />
    </div>

    <div v-if="notes && !loading" class="border-t border-line px-5 pb-5 pt-4 text-left">
      <p class="text-[13px] leading-relaxed text-ink">{{ notes.overview }}</p>
      <p class="mt-2 text-xs text-muted">字幕语言 {{ notes.language }} · {{ sourceLabel }}</p>

      <div class="mt-4 flex flex-wrap gap-2">
        <button
          v-for="item in tabs"
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
        <article v-for="(item, i) in notes.outline" :key="i" class="rounded-xl bg-surface px-3.5 py-3">
          <p class="text-xs text-muted">{{ item.timestamp }}</p>
          <h3 class="mt-0.5 text-sm font-semibold text-ink">{{ item.title }}</h3>
          <p v-if="item.summary" class="mt-1 text-[13px] leading-relaxed text-muted">{{ item.summary }}</p>
        </article>
        <p v-if="!notes.outline.length" class="text-sm text-muted">没有解析出章节。</p>
      </div>

      <ol v-else-if="tab === 'points'" class="mt-4 list-decimal space-y-2 pl-5 text-[13px] leading-relaxed text-ink">
        <li v-for="(p, i) in notes.key_points" :key="i">{{ p }}</li>
      </ol>

      <div v-else-if="tab === 'map'" class="mt-4 overflow-x-auto">
        <MindMapTree :node="notes.mind_map" :root="true" />
      </div>

      <div v-else class="mt-4 max-h-72 overflow-auto rounded-xl bg-surface px-3 py-3">
        <p v-for="(cue, i) in notes.transcript" :key="i" class="mb-2 text-[13px] leading-relaxed">
          <span class="mr-2 font-mono text-xs text-accent">{{ cue.timestamp }}</span>
          <span class="text-ink">{{ cue.text }}</span>
        </p>
      </div>

      <div class="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          class="rounded-lg border border-line px-3 py-2 text-xs font-medium text-ink hover:bg-surface"
          @click="copyMarkdown"
        >
          {{ copied ? '已复制' : '复制 Markdown' }}
        </button>
        <button
          type="button"
          class="rounded-lg border border-line px-3 py-2 text-xs font-medium text-ink hover:bg-surface"
          @click="exportMarkdown"
        >
          导出 Markdown
        </button>
        <button
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
