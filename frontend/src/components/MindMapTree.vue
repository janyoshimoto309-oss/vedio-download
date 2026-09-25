<script>
export default {
  name: 'MindMapTree',
  props: {
    node: { type: Object, required: true },
    root: { type: Boolean, default: false },
  },
}
</script>

<template>
  <div :class="root ? '' : 'ml-4 border-l border-line pl-3'">
    <p :class="root ? 'text-sm font-semibold text-ink' : 'mt-2 text-[13px] text-ink'">{{ node.label }}</p>
    <MindMapTree v-for="(child, i) in node.children || []" :key="i" :node="child" />
  </div>
</template>
