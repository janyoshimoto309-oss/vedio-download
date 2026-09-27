<script setup>
defineProps({
  tone: { type: String, default: 'danger' },
  title: { type: String, required: true },
  detail: { type: String, default: '' },
  wide: { type: Boolean, default: false },
})
</script>

<template>
  <div
    class="mx-auto mt-5 flex w-full gap-3 rounded-[14px] px-4 py-3.5"
    :class="[
      wide ? 'max-w-[1200px]' : 'max-w-search',
      tone === 'warn'
        ? 'border border-warn-border bg-warn-bg'
        : 'border border-danger-border bg-danger-bg',
    ]"
  >
    <svg
      class="mt-0.5 h-5 w-5 shrink-0"
      :class="tone === 'warn' ? 'text-warn' : 'text-danger'"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      aria-hidden="true"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
      />
    </svg>
    <div class="min-w-0">
      <p class="text-sm font-semibold" :class="tone === 'warn' ? 'text-warn' : 'text-danger'">{{ title }}</p>
      <p v-if="detail" class="mt-0.5 text-[13px] leading-relaxed text-ink">{{ detail }}</p>
    </div>
  </div>
</template>
