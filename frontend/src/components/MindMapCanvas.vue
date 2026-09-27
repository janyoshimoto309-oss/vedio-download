<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MindElixir from 'mind-elixir'
import { snapdom } from '@zumer/snapdom'
import 'mind-elixir/style.css'

const props = defineProps({
  node: { type: Object, required: true },
})

const emit = defineEmits(['error'])

const expanded = ref(false)
const inlineHost = ref(null)
const overlayHost = ref(null)

let mind = null
let resizeObserver = null
let fitTimer = 0
let prevBodyOverflow = ''

const THEME = {
  name: 'NotesLight',
  type: 'light',
  palette: ['#2563EB', '#1D4ED8', '#3B82F6', '#60A5FA', '#334155', '#0EA5E9', '#64748B', '#1E40AF'],
  cssVar: {
    '--main-color': '#1D4ED8',
    '--main-bgcolor': '#EFF6FF',
    '--color': '#0F172A',
    '--bgcolor': '#F7F8FA',
    '--selected': '#2563EB',
    '--root-color': '#FFFFFF',
    '--root-bgcolor': '#2563EB',
    '--root-border-color': '#1D4ED8',
    '--panel-color': '15, 23, 42',
    '--panel-bgcolor': '255, 255, 255',
  },
}

function clampLabel(text) {
  const value = String(text || '').trim() || '节点'
  return value.length > 40 ? `${value.slice(0, 39)}…` : value
}

function toNodeData(node, path) {
  const children = Array.isArray(node?.children) ? node.children.filter(Boolean) : []
  return {
    id: `mm-${path}`,
    topic: clampLabel(node?.label),
    expanded: true,
    children: children.map((child, index) => toNodeData(child, `${path}-${index}`)),
  }
}

function toData(node) {
  return {
    nodeData: toNodeData(node || { label: '视频内容', children: [] }, '0'),
    direction: MindElixir.SIDE,
  }
}

function currentHost() {
  return expanded.value ? overlayHost.value : inlineHost.value
}

function fit() {
  if (!mind) return
  try {
    mind.toCenter()
    mind.scaleFit()
  } catch {
    /* layout may not be ready yet */
  }
}

function scheduleFit() {
  window.clearTimeout(fitTimer)
  fitTimer = window.setTimeout(fit, 60)
}

function destroyMind() {
  window.clearTimeout(fitTimer)
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (!mind) return
  try {
    mind.destroy()
  } catch {
    /* host may already be gone */
  }
  mind = null
}

function createMind() {
  destroyMind()
  const el = currentHost()
  if (!el) return
  try {
    mind = new MindElixir({
      el,
      direction: MindElixir.SIDE,
      editable: false,
      contextMenu: false,
      toolBar: false,
      keypress: false,
      allowUndo: false,
      overflowHidden: true,
      compact: true,
      mouseSelectionButton: 2,
      mobileMultiSelect: false,
      handleWheel: expanded.value ? true : () => {},
      theme: THEME,
    })
    const failed = mind.init(toData(props.node))
    if (failed) {
      destroyMind()
      emit('error', '脑图渲染失败，请重新生成。')
      return
    }
  } catch {
    destroyMind()
    emit('error', '脑图渲染失败，请重新生成。')
    return
  }
  if (typeof mind.disableEdit === 'function') mind.disableEdit()
  resizeObserver = new ResizeObserver(() => {
    const box = el.getBoundingClientRect()
    if (box.width > 8 && box.height > 8) scheduleFit()
  })
  resizeObserver.observe(el)
  nextTick(scheduleFit)
}

function onEsc(event) {
  if (event.key !== 'Escape') return
  event.preventDefault()
  closeExpanded()
}

function lockScroll(on) {
  if (on) {
    prevBodyOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', onEsc)
  } else {
    document.body.style.overflow = prevBodyOverflow
    window.removeEventListener('keydown', onEsc)
  }
}

function openExpanded() {
  expanded.value = true
}

function closeExpanded() {
  expanded.value = false
}

onMounted(createMind)
onBeforeUnmount(() => {
  lockScroll(false)
  destroyMind()
})

watch(expanded, async (on) => {
  lockScroll(on)
  await nextTick()
  createMind()
})

watch(
  () => props.node,
  () => {
    if (!mind) {
      createMind()
      return
    }
    mind.refresh(toData(props.node))
    scheduleFit()
  },
  { deep: true },
)

async function exportPng(filename) {
  if (!mind?.nodes) throw new Error('脑图还没画好。')
  const result = await snapdom(mind.nodes, {
    backgroundColor: '#ffffff',
    scale: 2,
    embedFonts: true,
  })
  await result.download({ format: 'png', filename: filename || '思维导图' })
}

defineExpose({ exportPng })
</script>

<template>
  <div class="relative">
    <div
      v-show="!expanded"
      ref="inlineHost"
      class="mind-map-host w-full overflow-hidden rounded-xl border border-line bg-surface"
      role="img"
      aria-label="思维导图"
    />
    <button
      v-show="!expanded"
      type="button"
      class="absolute right-2 top-2 z-10 rounded-lg border border-line bg-raised/95 px-2.5 py-1.5 text-xs font-medium text-ink shadow-sm hover:bg-surface"
      @click="openExpanded"
    >
      全屏查看
    </button>

    <Teleport to="body">
      <div
        v-if="expanded"
        class="fixed inset-0 z-[80] flex flex-col bg-surface"
        role="dialog"
        aria-modal="true"
        aria-label="思维导图全屏"
      >
        <div class="flex shrink-0 items-center justify-between border-b border-line px-4 py-3">
          <p class="text-sm font-semibold text-ink">思维导图</p>
          <button
            type="button"
            class="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-ink hover:bg-surface"
            @click="closeExpanded"
          >
            关闭
          </button>
        </div>
        <div ref="overlayHost" class="mind-map-overlay min-h-0 flex-1 overflow-hidden bg-surface" />
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.mind-map-host {
  height: min(420px, 52vh);
  min-height: 280px;
}
.mind-map-overlay :deep(.map-container),
.mind-map-host :deep(.map-container) {
  height: 100%;
}
.mind-map-host :deep(me-root me-tpc),
.mind-map-overlay :deep(me-root me-tpc) {
  font-size: 16px;
  padding: 8px 16px;
}
.mind-map-host :deep(me-parent),
.mind-map-overlay :deep(me-parent) {
  cursor: grab;
}
.mind-map-host :deep(me-parent:active),
.mind-map-overlay :deep(me-parent:active) {
  cursor: grabbing;
}
</style>
