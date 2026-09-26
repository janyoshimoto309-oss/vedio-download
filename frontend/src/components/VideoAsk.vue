<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { askVideo, fetchNotesReady } from '../api/notes'

const props = defineProps({
  url: { type: String, required: true },
})

const llmReady = ref(true)
const draft = ref('')
const sending = ref(false)
const error = ref('')
const messages = ref([])
const thread = ref(null)

watch(
  () => props.url,
  () => {
    draft.value = ''
    sending.value = false
    error.value = ''
    messages.value = []
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

function scrollThread() {
  nextTick(() => {
    const el = thread.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

async function send() {
  const text = draft.value.trim()
  if (!text || sending.value || !llmReady.value || !props.url) return
  error.value = ''
  messages.value = [...messages.value, { role: 'user', content: text }].slice(-16)
  draft.value = ''
  sending.value = true
  scrollThread()
  try {
    const data = await askVideo(props.url, messages.value)
    messages.value = [...messages.value, { role: 'assistant', content: data.reply || '' }].slice(-16)
  } catch (e) {
    error.value = e.message || '回答失败'
  } finally {
    sending.value = false
    scrollThread()
  }
}

function onKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    send()
  }
}
</script>

<template>
  <section class="mx-auto mt-4 w-full max-w-search rounded-2xl border border-line bg-raised">
    <div class="p-5 text-left">
      <p class="text-sm font-semibold text-ink">问这个视频</p>
      <p class="mt-1 text-xs leading-relaxed text-muted">
        根据字幕回答。没有字幕轨时这里会失败，下载不受影响。
      </p>
      <p v-if="!llmReady" class="mt-1 text-xs text-warn">
        后端尚未读到 DeepSeek Key。问答暂不可用。
      </p>
    </div>

    <div
      v-if="messages.length || sending"
      ref="thread"
      class="max-h-80 space-y-3 overflow-auto border-t border-line px-5 py-4 text-left"
    >
      <div
        v-for="(item, i) in messages"
        :key="i"
        class="flex"
        :class="item.role === 'user' ? 'justify-end' : 'justify-start'"
      >
        <p
          class="max-w-[85%] whitespace-pre-wrap rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed"
          :class="item.role === 'user' ? 'bg-accent text-white' : 'bg-surface text-ink'"
        >
          {{ item.content }}
        </p>
      </div>
      <p v-if="sending" class="text-xs text-muted">正在回答…</p>
    </div>

    <p v-if="error" class="px-5 pb-2 text-left text-sm text-danger">{{ error }}</p>

    <form class="flex items-end gap-2 border-t border-line p-4" @submit.prevent="send">
      <textarea
        v-model="draft"
        rows="2"
        maxlength="2000"
        placeholder="问问这个视频讲了什么"
        :disabled="sending || !llmReady || !url"
        class="min-h-[44px] flex-1 resize-none rounded-xl border border-line bg-surface px-3 py-2 text-sm text-ink outline-none placeholder:text-muted disabled:opacity-70"
        @keydown="onKeydown"
      />
      <button
        type="submit"
        :disabled="sending || !llmReady || !url || !draft.trim()"
        class="h-10 shrink-0 rounded-xl bg-accent px-3.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-70"
      >
        发送
      </button>
    </form>
  </section>
</template>
