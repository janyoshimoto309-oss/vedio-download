<script setup>
import { ref } from 'vue'

defineProps({
  modelValue: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'parse'])

const inputRef = ref(null)

function onSubmit() {
  emit('parse')
}

function focus() {
  inputRef.value?.focus()
}

defineExpose({ focus })
</script>

<template>
  <form class="mx-auto w-full max-w-search" @submit.prevent="onSubmit">
    <div
      class="flex h-[60px] items-center gap-2.5 rounded-[30px] border border-accent bg-raised pl-5 pr-1.5 shadow-search"
    >
      <svg class="h-5 w-5 shrink-0 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M13.828 10.172a4 4 0 010 5.656l-1 1a4 4 0 01-5.656-5.656l1.5-1.5M10.172 13.828a4 4 0 010-5.656l1-1a4 4 0 015.656 5.656l-1.5 1.5"
        />
      </svg>
      <input
        ref="inputRef"
        :value="modelValue"
        type="text"
        required
        placeholder="粘贴 YouTube / B站 / 抖音链接，或抖音分享口令"
        class="min-w-0 flex-1 bg-transparent text-base text-ink outline-none placeholder:text-slate-400"
        @input="emit('update:modelValue', $event.target.value)"
      />
      <button
        type="submit"
        :disabled="loading"
        class="h-12 shrink-0 rounded-full bg-accent px-6 text-[15px] font-semibold text-white transition hover:bg-blue-700 disabled:opacity-70"
      >
        {{ loading ? '正在识别…' : '开始' }}
      </button>
    </div>
  </form>
</template>
