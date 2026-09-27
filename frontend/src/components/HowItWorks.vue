<template>
  <section class="mx-auto mt-16 w-full max-w-content pb-8">
    <div class="mx-auto w-full max-w-content">
      <p class="text-[13px] font-medium text-accent">贴一次，三件事都能做</p>
      <h2 class="mt-2 font-display text-[28px] font-semibold tracking-tight text-ink">先确认是这条，再保存或学习。</h2>
      <div class="mt-7 grid gap-4 md:grid-cols-3">
        <article
          v-for="step in steps"
          :key="step.title"
          class="rounded-2xl border border-line bg-raised px-[22px] py-6"
        >
          <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-soft text-accent">
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="step.icon" />
            </svg>
          </div>
          <h3 class="mt-3 text-base font-semibold text-ink">{{ step.title }}</h3>
          <p class="mt-1.5 text-[13px] leading-relaxed text-muted">{{ step.body }}</p>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
const steps = [
  {
    title: '保存文件',
    body: '选清晰度，一键下载去水印视频到本机。',
    icon: 'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4',
  },
  {
    title: '学习笔记',
    body: '大纲、要点、脑图、字幕都能生成。',
    icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253',
  },
  {
    title: '问AI',
    body: '针对这条视频向AI提问。',
    icon: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z',
  },
]
</script>
