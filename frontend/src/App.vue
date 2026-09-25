<script setup>
import { onMounted, ref } from 'vue'
import UrlSearch from './components/UrlSearch.vue'
import VideoResult from './components/VideoResult.vue'
import { downloadVideo, fetchHealth, fetchVideoInfo } from './api/video'

const url = ref('')
const parsing = ref(false)
const downloading = ref(false)
const info = ref(null)
const error = ref('')
const notice = ref('')

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

async function onDownload({ format_id, prefer_mode }) {
  error.value = ''
  downloading.value = true
  try {
    const res = await downloadVideo({
      url: url.value.trim(),
      format_id,
      prefer_mode,
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
</script>

<template>
  <div class="min-h-screen">
    <header class="border-b border-slate-100 bg-white">
      <div class="mx-auto flex max-w-5xl items-center px-4 py-3">
        <div class="flex items-center gap-2">
          <div
            class="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 text-sm font-bold text-white"
          >
            DL
          </div>
          <span class="text-sm font-semibold text-slate-800">万能视频下载</span>
        </div>
      </div>
    </header>

    <main class="px-4 pb-20 pt-12 md:pt-16">
      <div class="mx-auto max-w-3xl text-center">
        <h1 class="text-3xl font-bold tracking-tight text-slate-900 md:text-5xl">
          万能视频下载，
          <span class="bg-gradient-to-r from-indigo-500 to-purple-600 bg-clip-text text-transparent">一键保存</span>
        </h1>
        <p class="mt-4 text-sm text-slate-500 md:text-base">
          随时随地从多平台解析并下载。手机也能用。
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
    </main>

    <footer class="border-t border-slate-100 bg-white py-8 text-center text-xs text-slate-400">
      请尊重版权与平台规则，仅供个人学习使用。
    </footer>
  </div>
</template>
