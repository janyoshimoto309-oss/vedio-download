<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import UrlSearch from './components/UrlSearch.vue'
import VideoResult from './components/VideoResult.vue'
import HowItWorks from './components/HowItWorks.vue'
import StatusAlert from './components/StatusAlert.vue'
import ResultSkeleton from './components/ResultSkeleton.vue'
import { downloadVideo, fetchHealth, fetchVideoInfo } from './api/video'

const COPY = {
  idle: {
    headline: '看见喜欢的，就收进手机。',
    subhead: '把公开视频链接变成你能保存的文件。不用注册，手机也能用。',
  },
  parsing: {
    headline: '看见喜欢的，就收进手机。',
    subhead: '把公开视频链接变成你能保存的文件。不用注册，手机也能用。',
  },
  ready: {
    headline: '确认一下，再保存。',
    subhead: '封面和标题对上了，就可以选清晰度下载。',
  },
  downloading: {
    headline: '正在把文件准备好。',
    subhead: '高清画面会自动配上声音，稍等片刻即可保存。',
  },
  parseError: {
    headline: '这条链接还没法保存。',
    subhead: '换一条公开视频链接再试。不用注册，贴对就能开始。',
  },
  serviceDown: {
    headline: '稍后再来，也能马上开始。',
    subhead: '服务暂时连不上。链接先留着，恢复后贴上就能保存。',
  },
  downloadError: {
    headline: '这次没保存成功。',
    subhead: '换一个清晰度再试，或稍后再点开始下载。',
  },
}

const url = ref('')
const parsing = ref(false)
const downloading = ref(false)
const info = ref(null)
const error = ref('')
const notice = ref('')
const searchRef = ref(null)

const view = computed(() => {
  if (downloading.value) return 'downloading'
  if (info.value && error.value) return 'downloadError'
  if (info.value) return 'ready'
  if (parsing.value) return 'parsing'
  if (error.value) return 'parseError'
  if (notice.value) return 'serviceDown'
  return 'idle'
})

const copy = computed(() => COPY[view.value])
const showSearch = computed(() => !info.value)
const showSteps = computed(() => !info.value && !parsing.value)

const urlSnippet = computed(() => {
  try {
    const parsed = new URL(url.value.trim())
    const host = parsed.hostname.replace(/^www\./, '')
    const path = parsed.pathname.replace(/\/$/, '')
    const text = path ? `${host}${path}` : host
    return text.length > 28 ? `${text.slice(0, 26)}…` : text
  } catch {
    const raw = url.value.trim()
    return raw.length > 28 ? `${raw.slice(0, 26)}…` : raw
  }
})

const alert = computed(() => {
  if (view.value === 'parseError') {
    return {
      tone: 'danger',
      title: '无法识别这个链接',
      detail: error.value || '请确认是公开可访问的视频页，而不是首页、合集或需要登录的内容。',
    }
  }
  if (view.value === 'downloadError') {
    return {
      tone: 'danger',
      title: '下载失败',
      detail: error.value || '可以换一条清晰度，或过一会儿再试。视频信息还在，不用重新粘贴链接。',
    }
  }
  if (view.value === 'serviceDown') {
    return {
      tone: 'warn',
      title: '服务暂时不可用',
      detail: '请稍后再试。不需要注册，恢复后直接粘贴链接即可。',
    }
  }
  return null
})

onMounted(async () => {
  try {
    await fetchHealth()
  } catch {
    notice.value = '服务暂时不可用，请稍后再试。'
  }
})

async function onParse() {
  error.value = ''
  notice.value = ''
  info.value = null
  parsing.value = true
  try {
    info.value = await fetchVideoInfo(url.value.trim())
  } catch (e) {
    error.value = e.message || '解析失败'
  } finally {
    parsing.value = false
  }
}

async function onDownload({ format_id, prefer_mode, stream_kind }) {
  error.value = ''
  downloading.value = true
  try {
    const res = await downloadVideo({
      url: url.value.trim(),
      format_id,
      prefer_mode,
      stream_kind,
    })
    const href = res.mode === 'redirect' ? res.redirect_url : res.download_url
    if (!href) throw new Error('未返回下载地址')
    window.location.href = href
  } catch (e) {
    error.value = e.message || '下载失败'
  } finally {
    downloading.value = false
  }
}

async function onChangeLink() {
  url.value = ''
  info.value = null
  error.value = ''
  notice.value = ''
  downloading.value = false
  await nextTick()
  searchRef.value?.focus()
}
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <header class="border-b border-line bg-raised">
      <div class="mx-auto flex h-16 max-w-[1440px] items-center px-4 md:px-14">
        <div class="flex items-center gap-2.5">
          <div class="flex h-[30px] w-[30px] items-center justify-center rounded-[9px] bg-accent text-white">
            <svg class="h-[15px] w-[15px]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2.2"
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
          </div>
          <span class="text-sm font-semibold text-ink">万能视频下载</span>
        </div>
      </div>
    </header>

    <main class="relative flex-1 overflow-hidden px-4 pb-10 pt-10 md:pt-14">
      <div
        class="pointer-events-none absolute left-1/2 top-8 h-[280px] w-[520px] -translate-x-[70%] rounded-full bg-[#2563EB]/15 blur-3xl"
      />
      <div
        class="pointer-events-none absolute left-1/2 top-16 h-[240px] w-[420px] translate-x-[10%] rounded-full bg-[#38BDF8]/20 blur-3xl"
      />

      <div class="relative mx-auto max-w-content text-center">
        <p class="text-[13px] font-medium text-accent">一条链接 · 立刻留下</p>
        <h1 class="mt-3 font-display text-[32px] font-semibold leading-[1.15] tracking-tight text-ink md:text-[52px]">
          {{ copy.headline }}
        </h1>
        <p class="mx-auto mt-3 max-w-xl text-base text-muted md:text-lg">
          {{ copy.subhead }}
        </p>
      </div>

      <div class="relative mt-8">
        <UrlSearch v-if="showSearch" ref="searchRef" v-model="url" :loading="parsing" @parse="onParse" />
        <div
          v-else
          class="mx-auto flex h-[52px] w-full max-w-search items-center justify-between rounded-full border border-line bg-raised px-5"
        >
          <div class="flex min-w-0 items-center gap-2 text-sm">
            <svg class="h-4 w-4 shrink-0 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.2" d="M5 13l4 4L19 7" />
            </svg>
            <span class="shrink-0 font-medium text-ink">已识别</span>
            <span class="truncate text-muted">{{ urlSnippet }}</span>
          </div>
          <button type="button" class="shrink-0 text-sm font-medium text-accent hover:text-blue-700" @click="onChangeLink">
            更换链接
          </button>
        </div>
      </div>

      <p v-if="showSearch && !parsing" class="relative mt-4 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-[13px] text-muted">
        <span v-for="item in ['无需登录', '多平台直达', '手机同样好用']" :key="item" class="inline-flex items-center gap-1.5">
          <svg class="h-3.5 w-3.5 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.2" d="M5 13l4 4L19 7" />
          </svg>
          {{ item }}
        </span>
      </p>

      <StatusAlert v-if="alert" :tone="alert.tone" :title="alert.title" :detail="alert.detail" />
      <ResultSkeleton v-if="parsing" />
      <VideoResult v-if="info" :info="info" :downloading="downloading" @download="onDownload" />
      <HowItWorks v-if="showSteps" />
    </main>

    <footer class="border-t border-line bg-raised py-7 text-center text-xs text-muted">
      请尊重版权与平台规则，仅供个人学习使用。
    </footer>
  </div>
</template>
