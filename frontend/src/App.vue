<script setup>
import { onMounted, ref } from 'vue'
import UrlSearch from './components/UrlSearch.vue'
import VideoResult from './components/VideoResult.vue'
import FeatureCards from './components/FeatureCards.vue'
import { downloadVideo, fetchHealth, fetchVideoInfo } from './api/video'

const url = ref('')
const parsing = ref(false)
const downloading = ref(false)
const info = ref(null)
const error = ref('')
const notice = ref('')
const ffmpeg = ref(null)
const lastMode = ref(null)

onMounted(async () => {
  try {
    const h = await fetchHealth()
    ffmpeg.value = h.ffmpeg
    if (!h.ffmpeg) {
      notice.value = '未检测到 ffmpeg：部分需要合并的清晰度将无法服务端下载。'
    }
  } catch {
    notice.value = '后端未启动。请先在 backend 目录运行 uvicorn。'
  }
})

async function onParse() {
  error.value = ''
  notice.value = ''
  lastMode.value = null
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

async function onDownload({ format_id, prefer_mode }) {
  error.value = ''
  downloading.value = true
  try {
    const res = await downloadVideo({
      url: url.value.trim(),
      format_id,
      prefer_mode,
    })
    lastMode.value = res
    const href = res.mode === 'redirect' ? res.redirect_url : res.download_url
    if (!href) throw new Error('未返回下载地址')
    if (res.fallback) {
      notice.value = res.reason || '直链不可用，已自动改用服务端下载。'
    } else {
      notice.value = `实际模式：${res.mode}${res.reason ? ' · ' + res.reason : ''}`
    }
    window.location.href = href
  } catch (e) {
    error.value = e.message || '下载失败'
  } finally {
    downloading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen">
    <header class="border-b border-slate-100 bg-white">
      <div class="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <div class="flex items-center gap-2">
          <div
            class="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 text-sm font-bold text-white"
          >
            DL
          </div>
          <span class="text-sm font-semibold text-slate-800">万能视频下载</span>
        </div>
        <span class="text-xs text-slate-400">学习项目 · 无登录</span>
      </div>
    </header>

    <main class="px-4 pb-20 pt-12 md:pt-16">
      <div class="mx-auto max-w-3xl text-center">
        <h1 class="text-3xl font-bold tracking-tight text-slate-900 md:text-5xl">
          万能视频下载，
          <span class="bg-gradient-to-r from-indigo-500 to-purple-600 bg-clip-text text-transparent">一键保存</span>
        </h1>
        <p class="mt-4 text-sm text-slate-500 md:text-base">
          随时随地从多平台解析并下载。手机也能用。服务端落盘与直链双模式自动选择。
        </p>
      </div>

      <div class="mt-10">
        <UrlSearch v-model="url" :loading="parsing" @parse="onParse" />
      </div>

      <p v-if="error" class="mx-auto mt-6 max-w-3xl rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
        {{ error }}
      </p>
      <p
        v-else-if="notice"
        class="mx-auto mt-6 max-w-3xl rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm text-amber-800"
      >
        {{ notice }}
      </p>

      <VideoResult v-if="info" :info="info" :downloading="downloading" @download="onDownload" />

      <FeatureCards />
    </main>

    <footer class="border-t border-slate-100 bg-white py-8 text-center text-xs text-slate-400">
      请尊重版权与平台条款。本站基于 yt-dlp 封装，仅供学习研究。
      <span v-if="ffmpeg !== null" class="ml-2">ffmpeg: {{ ffmpeg ? '已就绪' : '未安装' }}</span>
      <span v-if="lastMode" class="ml-2">上次: {{ lastMode.mode }}</span>
    </footer>
  </div>
</template>
