<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  info: { type: Object, required: true },
  downloading: { type: Boolean, default: false },
})

const emit = defineEmits(['download'])

const formatId = ref(props.info.formats?.[0]?.format_id || '')
const preferMode = ref('auto')
const showAdvanced = ref(false)

const durationText = computed(() => {
  const d = props.info.duration
  if (!d) return '时长未知'
  const s = Math.floor(d % 60)
  const m = Math.floor((d / 60) % 60)
  const h = Math.floor(d / 3600)
  if (h) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
})

const modeLabel = computed(() => {
  const map = { server: '服务端下载', redirect: '直链重定向', proxy: '代理下载' }
  return map[props.info.recommended_mode] || props.info.recommended_mode
})

function formatSize(n) {
  if (!n) return ''
  if (n > 1024 * 1024 * 1024) return `${(n / 1024 / 1024 / 1024).toFixed(1)} GB`
  if (n > 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`
  return `${Math.round(n / 1024)} KB`
}

function submit() {
  emit('download', { format_id: formatId.value, prefer_mode: preferMode.value })
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
          <span class="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-600">{{ info.extractor }}</span>
          <span class="text-xs text-slate-500">{{ durationText }}</span>
        </div>
        <h2 class="text-lg font-semibold leading-snug text-slate-900">{{ info.title }}</h2>
        <p class="mt-3 text-sm text-slate-600">
          本次推荐：
          <span class="font-medium text-indigo-600">{{ modeLabel }}</span>
          <span class="mt-1 block text-xs text-slate-400">{{ info.recommended_reason }}</span>
        </p>
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
          {{ f.vcodec && f.acodec ? '· 音视频' : f.vcodec ? '· 仅画面' : f.acodec ? '· 仅音频' : '' }}
          {{ formatSize(f.filesize) ? '· ' + formatSize(f.filesize) : '' }}
          ({{ f.format_id }})
        </option>
      </select>

      <button type="button" class="mt-3 text-xs text-indigo-600" @click="showAdvanced = !showAdvanced">
        {{ showAdvanced ? '收起高级选项' : '高级：手动指定下载模式' }}
      </button>
      <div v-if="showAdvanced" class="mt-2 flex flex-wrap gap-3 text-sm">
        <label class="flex items-center gap-1.5">
          <input v-model="preferMode" type="radio" value="auto" /> 自动
        </label>
        <label class="flex items-center gap-1.5">
          <input v-model="preferMode" type="radio" value="server" /> 强制服务端
        </label>
        <label class="flex items-center gap-1.5">
          <input v-model="preferMode" type="radio" value="direct" /> 优先直链
        </label>
      </div>

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
