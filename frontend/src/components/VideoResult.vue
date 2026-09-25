<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  info: { type: Object, required: true },
  downloading: { type: Boolean, default: false },
})

const emit = defineEmits(['download'])

const formatId = ref(props.info.formats?.[0]?.format_id || '')

const durationText = computed(() => {
  const d = props.info.duration
  if (!d) return '时长未知'
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
  if (n > 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`
  return `${Math.round(n / 1024)} KB`
}

const STREAM_LABELS = {
  muxed: '· 音视频',
  merge: '· 视频+音频合并',
  audio: '· 仅音频',
}

function streamLabel(f) {
  if (STREAM_LABELS[f.stream_kind]) return STREAM_LABELS[f.stream_kind]
  if (f.vcodec && f.acodec) return STREAM_LABELS.muxed
  if (f.vcodec) return STREAM_LABELS.merge
  if (f.acodec) return STREAM_LABELS.audio
  return ''
}

function submit() {
  emit('download', { format_id: formatId.value, prefer_mode: 'auto' })
}
</script>

<template>
  <section class="mx-auto mt-10 w-full max-w-3xl overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-sm">
    <div class="flex flex-col gap-5 p-5 md:flex-row md:p-6">
      <img
        v-if="info.thumbnail"
        :src="info.thumbnail"
        :alt="info.title"
        class="h-40 w-full rounded-xl object-cover md:h-36 md:w-56"
      />
      <div class="min-w-0 flex-1">
        <div class="mb-2 flex flex-wrap items-center gap-2">
          <span class="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-600">{{ platformLabel }}</span>
          <span class="text-xs text-slate-500">{{ durationText }}</span>
        </div>
        <h2 class="text-lg font-semibold leading-snug text-slate-900">{{ info.title }}</h2>
      </div>
    </div>

    <div class="border-t border-slate-100 px-5 py-5 md:px-6">
      <label class="mb-2 block text-sm font-medium text-slate-700">选择清晰度</label>
      <select
        v-model="formatId"
        class="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none focus:border-indigo-400"
      >
        <option v-for="f in info.formats" :key="f.format_id" :value="f.format_id">
          {{ f.resolution }} · {{ f.ext }}
          {{ streamLabel(f) }}
          {{ formatSize(f.filesize) ? '· ' + formatSize(f.filesize) : '' }}
        </option>
      </select>

      <button
        type="button"
        :disabled="downloading || !formatId"
        class="mt-5 w-full rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 py-3 text-sm font-semibold text-white disabled:opacity-60"
        @click="submit"
      >
        {{ downloading ? '正在准备下载…' : '开始下载' }}
      </button>
    </div>
  </section>
</template>
