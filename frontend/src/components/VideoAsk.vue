<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { askVideo, fetchNotesReady } from '../api/notes'

const props = defineProps({
  url: { type: String, required: true },
  embedded: { type: Boolean, default: false },
  inset: { type: Boolean, default: false },
  pane: { type: Boolean, default: false },
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
    requestAnimationFrame(() => {
      const el = thread.value
      if (el) el.scrollTop = el.scrollHeight
    })
  })
}

watch(
  () => messages.value.length,
  () => scrollThread(),
)

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
  <section
    class="flex w-full min-h-0 flex-col overflow-hidden"
    :class="
      pane
        ? 'h-full bg-raised'
        : inset
          ? 'shrink-0 border-t border-line bg-surface/80'
          : embedded
            ? 'shrink-0 rounded-2xl border border-line bg-raised'
            : 'mx-auto mt-4 max-w-search rounded-2xl border border-line bg-raised'
    "
  >
    <div
      v-show="messages.length || sending"
      ref="thread"
      class="min-h-0 space-y-3 overflow-y-auto overscroll-contain px-5 py-3 text-left"
      :class="pane ? 'flex-1' : inset ? 'max-h-52 lg:max-h-64' : embedded ? 'max-h-56 lg:max-h-72' : 'max-h-80'"
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

    <p v-if="error" class="px-5 pb-1 text-left text-sm text-danger">{{ error }}</p>

    <form
      class="flex shrink-0 flex-col gap-2 px-5 py-4"
      :class="[
        pane ? 'mt-auto border-t border-line' : '',
        !pane && (messages.length || sending) ? 'border-t border-line/80' : '',
      ]"
      @submit.prevent="send"
    >
      <div v-if="!pane" class="flex items-center justify-between gap-2">
        <p class="text-sm font-semibold text-ink">问AI</p>
        <p v-if="!llmReady" class="text-xs text-warn">问答暂时不可用</p>
      </div>
      <p v-else-if="!llmReady" class="text-xs text-warn">问答暂时不可用</p>
      <div class="flex items-end gap-2">
      <textarea
        v-model="draft"
        rows="2"
        maxlength="2000"
        placeholder="例如：他的结论是什么"
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
      </div>
    </form>
  </section>
</template>
