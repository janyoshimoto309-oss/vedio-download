<script setup>
defineProps({
  modelValue: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'parse'])

function onSubmit() {
  emit('parse')
}
</script>

<template>
  <form class="mx-auto w-full max-w-3xl" @submit.prevent="onSubmit">
    <div
      class="flex items-center gap-2 rounded-full border border-slate-200 bg-white p-1.5 shadow-sm md:p-2"
    >
      <svg class="ml-3 h-5 w-5 shrink-0 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 010 5.656l-1 1a4 4 0 01-5.656-5.656l1.5-1.5" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.172 13.828a4 4 0 010-5.656l1-1a4 4 0 015.656 5.656l-1.5 1.5" />
      </svg>
      <input
        :value="modelValue"
        type="url"
        required
        placeholder="粘贴 YouTube / B站 / 抖音 等视频链接"
        class="min-w-0 flex-1 bg-transparent px-1 py-2 text-base outline-none placeholder:text-slate-400"
        @input="emit('update:modelValue', $event.target.value)"
      />
      <button
        type="submit"
        :disabled="loading"
        class="shrink-0 rounded-full bg-gradient-to-r from-indigo-500 to-purple-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm disabled:opacity-60 md:px-7"
      >
        {{ loading ? '解析中…' : '解析' }}
      </button>
    </div>
  </form>
</template>
