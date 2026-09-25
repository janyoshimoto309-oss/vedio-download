<template>
  <section class="mx-auto mt-16 w-full max-w-content px-1 pb-8">
    <p class="text-[13px] font-medium text-accent">三步完成，不用下载任何 App</p>
    <h2 class="mt-2 font-display text-[28px] font-semibold tracking-tight text-ink">像复制一段话一样简单。</h2>
    <div class="mt-7 grid gap-4 md:grid-cols-3">
      <article
        v-for="step in steps"
        :key="step.n"
        class="rounded-2xl border border-line bg-raised px-[22px] py-6"
      >
        <p class="font-display text-[22px] font-semibold text-ink/90">{{ step.n }}</p>
        <h3 class="mt-3 text-base font-semibold text-ink">{{ step.title }}</h3>
        <p class="mt-1.5 text-[13px] leading-relaxed text-muted">{{ step.body }}</p>
      </article>
    </div>
  </section>
</template>

<script setup>
const steps = [
  { n: '01', title: '粘贴链接', body: '从你正在看的页面拷贝网址链接，贴进来即可。' },
  { n: '02', title: '选清晰度', body: '看到封面和标题再下。高清会自动带上声音。' },
  { n: '03', title: '保存文件', body: '一键下载到本机。完整视频，不是截图。' },
]
</script>
