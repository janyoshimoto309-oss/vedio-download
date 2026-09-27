<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  info: { type: Object, required: true },
  downloading: { type: Boolean, default: false },
  embedded: { type: Boolean, default: false },
})

const emit = defineEmits(['download'])

const formatId = ref('')
const open = ref(false)
const rootRef = ref(null)

watch(
  () => props.info,
  (val) => {
    formatId.value = val.formats?.[0]?.format_id || ''
  },
  { immediate: true },
)

const selected = computed(() => props.info.formats?.find((f) => f.format_id === formatId.value) || null)

const durationText = computed(() => {
  const d = props.info.duration
  if (!d) return ''
  const s = Math.floor(d % 60)
  const m = Math.floor((d / 60) % 60)
  const h = Math.floor(d / 3600)
  if (h) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
})

const platformLabel = computed(() => {
  const raw = String(props.info.extractor || '').trim()
  const key = raw.toLowerCase()
  if (key.includes('bili')) return 'B 站'
  if (key.includes('youtube')) return 'YouTube'
  if (key.includes('douyin')) return '抖音'
  if (key.includes('tiktok')) return 'TikTok'
  if (key.includes('kuaishou')) return '快手'
  if (key.includes('xiaohongshu') || key === 'xhs') return '小红书'
  if (key.includes('weibo')) return '微博'
  if (key.includes('youku')) return '优酷'
  if (key.includes('iqiyi') || key.includes('qiyi')) return '爱奇艺'
  if (key.includes('tencent') || key.includes('qq')) return '腾讯视频'
  if (key.includes('twitter') || key === 'x') return 'X'
  if (key.includes('instagram')) return 'Instagram'
  if (key.includes('facebook')) return 'Facebook'
  if (key.includes('vimeo')) return 'Vimeo'
  return raw || '未知来源'
})

function formatSize(n) {
  if (!n) return ''
  if (n > 1024 * 1024 * 1024) return `${(n / 1024 / 1024 / 1024).toFixed(1)} GB`
  if (n > 1024 * 1024) return `${(n / 1024 / 1024).toFixed(0)} MB`
  return `${Math.round(n / 1024)} KB`
}

function streamLabel(f) {
  if (f.stream_kind === 'muxed') return '含声音'
  if (f.stream_kind === 'merge') return '视频+音频合并'
  if (f.stream_kind === 'audio') return '仅音频'
  if (f.vcodec && f.acodec) return '含声音'
  if (f.vcodec) return '视频+音频合并'
  if (f.acodec) return '仅音频'
  return ''
}

function optionMeta(f) {
  const size = formatSize(f.filesize)
  const kind = streamLabel(f)
  if (size && kind) return `约 ${size} · ${kind}`
  if (size) return `约 ${size}`
  return kind
}

function pick(id) {
  formatId.value = id
  open.value = false
}

function submit() {
  emit('download', {
    format_id: formatId.value,
    prefer_mode: 'auto',
    stream_kind: selected.value?.stream_kind,
  })
}

function onDocClick(e) {
  if (!rootRef.value?.contains(e.target)) open.value = false
}

onMounted(() => document.addEventListener('click', onDocClick))
onUnmounted(() => document.removeEventListener('click', onDocClick))
</script>

<template>
  <section
    class="w-full rounded-2xl border border-line bg-raised"
    :class="embedded ? '' : 'mx-auto mt-8 max-w-search'"
  >
    <div class="flex flex-col gap-5 p-5 md:flex-row md:p-5">
      <img
        v-if="info.thumbnail"
        :src="info.thumbnail"
        :alt="info.title"
        class="h-36 w-full rounded-[10px] object-cover md:h-[112px] md:w-[200px] md:shrink-0"
      />
      <div
        v-else
        class="h-36 w-full rounded-[10px] bg-skeleton md:h-[112px] md:w-[200px] md:shrink-0"
      />
      <div class="min-w-0 flex-1">
        <div class="mb-2 flex flex-wrap items-center gap-2">
          <span class="rounded-full bg-accent-soft px-2.5 py-1 text-xs font-medium text-accent">{{ platformLabel }}</span>
          <span v-if="durationText" class="text-xs text-muted">{{ durationText }}</span>
        </div>
        <h2 class="text-[17px] font-semibold leading-snug text-ink">{{ info.title }}</h2>
      </div>
    </div>

    <div class="space-y-3 px-5 pb-5">
      <p class="text-sm font-medium text-ink">清晰度</p>
      <div ref="rootRef" class="relative">
        <button
          type="button"
          class="flex w-full items-center justify-between rounded-xl bg-surface px-3.5 py-3 text-left"
          @click="open = !open"
        >
          <span class="min-w-0">
            <span class="block text-sm font-medium text-ink">{{ selected?.resolution || '选择清晰度' }}</span>
            <span v-if="selected" class="mt-0.5 block text-xs text-muted">{{ optionMeta(selected) }}</span>
          </span>
          <svg
            class="h-4 w-4 shrink-0 text-muted transition-transform"
            :class="open ? 'rotate-180' : ''"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        <ul
          v-if="open"
          class="absolute bottom-full left-0 z-20 mb-1 max-h-60 w-full overflow-auto rounded-xl border border-line bg-raised py-1 shadow-lg"
        >
          <li v-for="f in info.formats" :key="f.format_id">
            <button
              type="button"
              class="flex w-full flex-col px-3.5 py-2.5 text-left hover:bg-accent-soft"
              :class="f.format_id === formatId ? 'bg-accent-soft' : ''"
              @click="pick(f.format_id)"
            >
              <span class="text-sm font-medium text-ink">{{ f.resolution }}</span>
              <span class="text-xs text-muted">{{ optionMeta(f) }}</span>
            </button>
          </li>
        </ul>
      </div>

      <button
        type="button"
        :disabled="downloading || !formatId"
        class="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-accent text-[15px] font-semibold text-white transition hover:bg-blue-700 disabled:opacity-70"
        @click="submit"
      >
        <svg v-if="!downloading" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
          />
        </svg>
        {{ downloading ? '正在准备下载…' : '开始下载' }}
      </button>
    </div>
  </section>
</template>
