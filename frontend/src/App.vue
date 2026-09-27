<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import UrlSearch from './components/UrlSearch.vue'
import VideoResult from './components/VideoResult.vue'
import VideoStudyNotes from './components/VideoStudyNotes.vue'
import VideoAsk from './components/VideoAsk.vue'
import HowItWorks from './components/HowItWorks.vue'
import StatusAlert from './components/StatusAlert.vue'
import ResultSkeleton from './components/ResultSkeleton.vue'
import { downloadVideo, fetchHealth, fetchVideoInfo } from './api/video'

const COPY = {
  idle: {
    headline: '贴上链接，留下文件，也留下理解。',
    subhead: '公开视频贴进来就能下。有字幕的，还能整理大纲、要点，并针对这条视频提问。',
  },
  parsing: {
    headline: '贴上链接，留下文件，也留下理解。',
    subhead: '公开视频贴进来就能下。有字幕的，还能整理大纲、要点，并针对这条视频提问。',
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
    subhead: '换一条公开视频链接再试。贴对就能开始。',
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
const studyPane = ref('notes')

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
    const bot = /机器人|not a bot|Sign in to confirm/i.test(error.value || '')
    return {
      tone: 'danger',
      title: bot ? '油管暂时拦了一下' : '无法识别这个链接',
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
      detail: '请稍后再试。恢复后直接粘贴链接即可。',
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

watch(url, () => {
  studyPane.value = 'notes'
})

async function onParse() {
  error.value = ''
  notice.value = ''
  info.value = null
  studyPane.value = 'notes'
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

    <main
      class="relative flex-1 px-4 pb-10 md:px-8"
      :class="info ? 'overflow-visible pt-4 md:pt-5' : 'overflow-visible pt-10 md:pt-14'"
    >
      <div
        v-if="!info"
        class="pointer-events-none absolute left-1/2 top-8 h-[280px] w-[520px] -translate-x-[70%] rounded-full bg-[#2563EB]/15 blur-3xl"
      />
      <div
        v-if="!info"
        class="pointer-events-none absolute left-1/2 top-16 h-[240px] w-[420px] translate-x-[10%] rounded-full bg-[#38BDF8]/20 blur-3xl"
      />

      <div v-if="!info" class="relative mx-auto max-w-content text-center">
        <h1 class="font-display text-[32px] font-semibold leading-[1.15] tracking-tight text-ink md:text-[52px]">
          {{ copy.headline }}
        </h1>
        <p class="mx-auto mt-3 max-w-2xl text-base text-muted md:text-lg">
          {{ copy.subhead }}
        </p>
      </div>

      <div class="relative" :class="info ? 'mx-auto max-w-[1200px]' : 'mt-8'">
        <UrlSearch v-if="showSearch" ref="searchRef" v-model="url" :loading="parsing" @parse="onParse" />
        <div
          v-else
          class="flex h-[52px] w-full items-center justify-between rounded-full border border-line bg-raised px-5"
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

      <StatusAlert v-if="alert" :tone="alert.tone" :title="alert.title" :detail="alert.detail" :wide="Boolean(info)" />
      <ResultSkeleton v-if="parsing" />

      <div
        v-if="info"
        class="relative mx-auto mt-5 grid w-full max-w-[1200px] items-start gap-5 lg:grid-cols-[minmax(320px,400px)_minmax(0,1fr)] lg:items-stretch lg:h-[calc(100dvh-10rem)] lg:min-h-[560px]"
      >
        <div class="lg:sticky lg:top-4 lg:self-start">
          <VideoResult embedded :info="info" :downloading="downloading" @download="onDownload" />
        </div>
        <section
          class="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-2xl border border-line bg-raised shadow-[0_1px_2px_rgba(15,23,42,0.04)] lg:h-full lg:min-h-0"
        >
          <div class="shrink-0 border-b border-line px-4 pb-4 pt-4">
            <div class="grid grid-cols-2 gap-1 rounded-xl bg-surface p-1" role="tablist">
              <button
                type="button"
                role="tab"
                class="h-10 rounded-lg text-sm font-semibold transition"
                :class="studyPane === 'notes' ? 'bg-raised text-ink shadow-sm' : 'text-muted hover:text-ink'"
                :aria-selected="studyPane === 'notes'"
                @click="studyPane = 'notes'"
              >
                学习笔记
              </button>
              <button
                type="button"
                role="tab"
                class="h-10 rounded-lg text-sm font-semibold transition"
                :class="studyPane === 'ask' ? 'bg-raised text-ink shadow-sm' : 'text-muted hover:text-ink'"
                :aria-selected="studyPane === 'ask'"
                @click="studyPane = 'ask'"
              >
                问AI
              </button>
            </div>
          </div>
          <div class="relative min-h-0 flex-1 overflow-hidden">
            <div
              v-show="studyPane === 'notes'"
              class="h-full overflow-y-auto overscroll-contain"
            >
              <VideoStudyNotes embedded inset :url="url" />
            </div>
            <div
              v-show="studyPane === 'ask'"
              class="flex h-full min-h-0 flex-col"
            >
              <VideoAsk embedded inset pane :url="url" />
            </div>
          </div>
        </section>
      </div>

      <HowItWorks v-if="showSteps" />
    </main>

    <footer
      class="border-t border-line bg-raised text-center text-xs text-muted"
      :class="info ? 'py-4' : 'py-7'"
    >
      请尊重版权与平台规则，仅供个人学习使用。
    </footer>
  </div>
</template>
