<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from 'vue'

import { GRAPH_TYPES } from '../utils/graph'

const props = defineProps({
  graph: { type: Object, default: () => ({ nodes: [], edges: [] }) },
  height: { type: Number, default: 420 },
  compact: { type: Boolean, default: false },
  interactive: { type: Boolean, default: true },
})

const emit = defineEmits(['select'])

const container = ref(null)
const svgEl = ref(null)
const width = ref(720)
const nodes = ref([])
const edges = ref([])
const scale = ref(1)
const tx = ref(0)
const ty = ref(0)
const selectedId = ref(null)
const hoverId = ref(null)
const dragState = reactive({ active: false })

const markerId = `graph-arrow-${Math.random().toString(36).slice(2, 9)}`
const activeId = computed(() => selectedId.value || hoverId.value)

const nodeMap = computed(() => {
  const map = new Map()
  nodes.value.forEach((node) => map.set(node.id, node))
  return map
})

const neighbors = computed(() => {
  const set = new Set()
  if (!activeId.value) return set
  set.add(activeId.value)
  for (const edge of edges.value) {
    if (edge.source === activeId.value) set.add(edge.target)
    if (edge.target === activeId.value) set.add(edge.source)
  }
  return set
})

const lines = computed(() =>
  edges.value
    .map((edge) => {
      const source = nodeMap.value.get(edge.source)
      const target = nodeMap.value.get(edge.target)
      if (!source || !target) return null

      const dx = target.x - source.x
      const dy = target.y - source.y
      const distance = Math.max(1, Math.hypot(dx, dy))
      const r1 = radiusOf(source) + 3
      const r2 = radiusOf(target) + 5

      return {
        edge,
        x1: source.x + (dx / distance) * r1,
        y1: source.y + (dy / distance) * r1,
        x2: target.x - (dx / distance) * r2,
        y2: target.y - (dy / distance) * r2,
        mx: (source.x + target.x) / 2,
        my: (source.y + target.y) / 2,
      }
    })
    .filter(Boolean),
)

function metaOf(type) {
  return GRAPH_TYPES[type] || GRAPH_TYPES.CONCEPT
}

function colorOf(type) {
  return metaOf(type).color
}

function radiusOf(node) {
  const base = props.compact ? 4.6 : 6.2
  return base + Math.min(4.2, (node.degree || 0) * 0.72)
}

function shortLabel(label) {
  const text = String(label || '')
  return text.length > 26 ? `${text.slice(0, 24)}…` : text
}

function showLabel(node) {
  if (!props.compact) return true
  return node.degree >= 2 || activeId.value === node.id
}

function isDimNode(node) {
  if (!activeId.value) return false
  return !neighbors.value.has(node.id)
}

function isDimEdge(line) {
  if (!activeId.value) return false
  return line.edge.source !== activeId.value && line.edge.target !== activeId.value
}

function edgeIsActive(line) {
  return (
    selectedId.value &&
    (line.edge.source === selectedId.value || line.edge.target === selectedId.value)
  )
}

function buildDegrees(edgeList) {
  const degrees = {}
  for (const edge of edgeList) {
    degrees[edge.source] = (degrees[edge.source] || 0) + 1
    degrees[edge.target] = (degrees[edge.target] || 0) + 1
  }
  return degrees
}

function init() {
  const sourceNodes = props.graph?.nodes || []
  const sourceEdges = props.graph?.edges || []
  const rect = container.value?.getBoundingClientRect()
  width.value = Math.max(260, Math.round(rect?.width || 720))

  const degrees = buildDegrees(sourceEdges)
  const count = Math.max(1, sourceNodes.length)
  const centerX = width.value / 2
  const centerY = props.height / 2
  const orbit = Math.min(
    width.value * 0.34,
    props.height * (props.compact ? 0.34 : 0.38),
  )

  nodes.value = sourceNodes.map((node, index) => {
    const angle = -Math.PI / 2 + (index / count) * Math.PI * 2
    const wobble = ((index * 37) % 11) - 5
    return {
      ...node,
      x: centerX + Math.cos(angle) * orbit + wobble,
      y: centerY + Math.sin(angle) * orbit + wobble * 0.6,
      vx: 0,
      vy: 0,
      degree: degrees[node.id] || 0,
    }
  })

  edges.value = sourceEdges.map((edge) => ({ ...edge }))
  selectedId.value = null
  hoverId.value = null
  scale.value = 1
  tx.value = 0
  ty.value = 0
  wake()
}

let raf = null
let running = false
let frames = 0
let resizeObserver = null
let panning = null
let dragging = null
let windowBound = false

function wake() {
  if (!props.interactive && running) return
  frames = 0
  if (running) return
  running = true
  raf = requestAnimationFrame(tick)
}

function tick() {
  raf = null
  step()
  if (running) raf = requestAnimationFrame(tick)
}

function step() {
  const list = nodes.value
  if (!list.length) {
    running = false
    return
  }

  const w = width.value
  const h = props.height
  const cx = w / 2
  const cy = h / 2
  const repulsion = props.compact ? 1500 : 2600
  const linkLength = props.compact ? 58 : 100
  const linkStrength = props.compact ? 0.016 : 0.012

  for (const node of list) {
    node.fx = 0
    node.fy = 0
  }

  for (let i = 0; i < list.length; i += 1) {
    for (let j = i + 1; j < list.length; j += 1) {
      const a = list[i]
      const b = list[j]
      let dx = b.x - a.x
      let dy = b.y - a.y
      if (dx === 0 && dy === 0) {
        dx = (i + 1) * 0.01
        dy = (j + 1) * 0.01
      }
      const distance = Math.max(1, Math.hypot(dx, dy))
      const force = repulsion / Math.max(900, distance * distance)
      const ux = dx / distance
      const uy = dy / distance
      a.fx -= ux * force
      a.fy -= uy * force
      b.fx += ux * force
      b.fy += uy * force
    }
  }

  const map = nodeMap.value
  for (const edge of edges.value) {
    const a = map.get(edge.source)
    const b = map.get(edge.target)
    if (!a || !b) continue
    const dx = b.x - a.x
    const dy = b.y - a.y
    const distance = Math.max(1, Math.hypot(dx, dy))
    const force = (distance - linkLength) * linkStrength
    const ux = dx / distance
    const uy = dy / distance
    a.fx += ux * force
    a.fy += uy * force
    b.fx -= ux * force
    b.fy -= uy * force
  }

  let maxSpeed = 0
  for (const node of list) {
    node.fx += (cx - node.x) * 0.0035
    node.fy += (cy - node.y) * 0.0035

    if (dragging && dragging.node === node) {
      node.vx = 0
      node.vy = 0
      continue
    }

    node.vx = (node.vx + node.fx) * 0.86
    node.vy = (node.vy + node.fy) * 0.86
    node.x += node.vx
    node.y += node.vy

    const padX = radiusOf(node) + (props.compact ? 14 : 26)
    const padTop = radiusOf(node) + (props.compact ? 12 : 24)
    const padBottom = radiusOf(node) + (props.compact ? 18 : 36)
    node.x = Math.min(w - padX, Math.max(padX, node.x))
    node.y = Math.min(h - padBottom, Math.max(padTop, node.y))

    maxSpeed = Math.max(maxSpeed, Math.hypot(node.vx, node.vy))
  }

  frames += 1
  if (frames > 80 && maxSpeed < 0.06) {
    running = false
  }
}

function selectNode(node, event) {
  if (!props.interactive) return
  event.stopPropagation()
  selectedId.value = node.id
  emit('select', {
    id: node.id,
    label: node.label,
    type: node.type,
    degree: node.degree,
  })
}

function startDrag(event, node) {
  if (!props.interactive || event.button !== 0) return
  event.preventDefault()
  event.stopPropagation()
  selectedId.value = node.id
  emit('select', {
    id: node.id,
    label: node.label,
    type: node.type,
    degree: node.degree,
  })

  const rect = svgEl.value.getBoundingClientRect()
  const gx = (event.clientX - rect.left - tx.value) / scale.value
  const gy = (event.clientY - rect.top - ty.value) / scale.value
  dragging = { node, offsetX: node.x - gx, offsetY: node.y - gy }
  dragState.active = true
  bindWindow()
  wake()
}

function onBackgroundDown(event) {
  if (!props.interactive || event.button !== 0) return
  if (event.target !== svgEl.value) return
  selectedId.value = null
  emit('select', null)
  panning = {
    startX: event.clientX,
    startY: event.clientY,
    tx: tx.value,
    ty: ty.value,
    moved: false,
  }
  bindWindow()
}

function bindWindow() {
  if (windowBound) return
  windowBound = true
  window.addEventListener('pointermove', onWindowMove)
  window.addEventListener('pointerup', onWindowUp)
  window.addEventListener('pointercancel', onWindowUp)
}

function releaseWindow() {
  windowBound = false
  window.removeEventListener('pointermove', onWindowMove)
  window.removeEventListener('pointerup', onWindowUp)
  window.removeEventListener('pointercancel', onWindowUp)
}

function onWindowMove(event) {
  if (dragging) {
    const rect = svgEl.value.getBoundingClientRect()
    const gx = (event.clientX - rect.left - tx.value) / scale.value
    const gy = (event.clientY - rect.top - ty.value) / scale.value
    dragging.node.x = gx + dragging.offsetX
    dragging.node.y = gy + dragging.offsetY
    dragging.node.vx = 0
    dragging.node.vy = 0
    wake()
  } else if (panning) {
    const dx = event.clientX - panning.startX
    const dy = event.clientY - panning.startY
    if (Math.abs(dx) + Math.abs(dy) > 2) panning.moved = true
    tx.value = panning.tx + dx
    ty.value = panning.ty + dy
  }
}

function onWindowUp() {
  dragging = null
  panning = null
  dragState.active = false
  releaseWindow()
}

function onWheel(event) {
  if (!props.interactive) return
  const rect = svgEl.value.getBoundingClientRect()
  const px = event.clientX - rect.left
  const py = event.clientY - rect.top
  const next = Math.min(2.4, Math.max(0.55, scale.value * Math.exp(-event.deltaY * 0.0012)))
  const ratio = next / scale.value
  tx.value = px - (px - tx.value) * ratio
  ty.value = py - (py - ty.value) * ratio
  scale.value = next
}

function zoomBy(factor) {
  const px = width.value / 2
  const py = props.height / 2
  const next = Math.min(2.4, Math.max(0.55, scale.value * factor))
  const ratio = next / scale.value
  tx.value = px - (px - tx.value) * ratio
  ty.value = py - (py - ty.value) * ratio
  scale.value = next
}

function resetView() {
  scale.value = 1
  tx.value = 0
  ty.value = 0
}

function focusNode(id) {
  const node = nodes.value.find((item) => item.id === id)
  if (!node) return
  selectedId.value = id
  emit('select', {
    id: node.id,
    label: node.label,
    type: node.type,
    degree: node.degree,
  })
  const nextScale = Math.max(scale.value, 1.25)
  scale.value = nextScale
  tx.value = width.value / 2 - node.x * nextScale
  ty.value = props.height / 2 - node.y * nextScale
}

function clearSelection() {
  selectedId.value = null
  emit('select', null)
}

defineExpose({ zoomBy, resetView, focusNode, clearSelection })

let stopHeightWatch = null

onMounted(async () => {
  await nextTick()
  init()
  resizeObserver = new ResizeObserver((entries) => {
    const next = Math.max(260, Math.round(entries[0].contentRect.width))
    if (Math.abs(next - width.value) > 1) {
      width.value = next
      wake()
    }
  })
  if (container.value) resizeObserver.observe(container.value)

  stopHeightWatch = watch(
    () => props.height,
    () => init(),
  )
})

watch(
  () => props.graph,
  () => init(),
)

onBeforeUnmount(() => {
  if (raf) cancelAnimationFrame(raf)
  resizeObserver?.disconnect()
  releaseWindow()
  stopHeightWatch?.()
})
</script>

<template>
  <div
    ref="container"
    class="graph"
    :class="{ 'is-compact': compact }"
    :style="{ height: `${height}px` }"
  >
    <svg
      ref="svgEl"
      class="graph-svg"
      :class="{ 'is-panning': dragState.active }"
      :viewBox="`0 0 ${width} ${height}`"
      preserveAspectRatio="xMidYMid meet"
      @pointerdown="onBackgroundDown"
      @wheel.prevent="onWheel"
    >
      <defs>
        <marker
          :id="markerId"
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="4.5"
          markerHeight="4.5"
          orient="auto-start-reverse"
        >
          <path d="M 0 1 L 9 5 L 0 9 z" fill="#b9cce8" />
        </marker>
      </defs>

      <g :transform="`translate(${tx} ${ty}) scale(${scale})`">
        <g class="edges">
          <line
            v-for="(line, index) in lines"
            :key="`e-${index}`"
            :x1="line.x1"
            :y1="line.y1"
            :x2="line.x2"
            :y2="line.y2"
            :class="{ 'is-dim': isDimEdge(line), 'is-active': edgeIsActive(line) }"
            :marker-end="`url(#${markerId})`"
          />
          <text
            v-for="(line, index) in lines"
            v-show="edgeIsActive(line)"
            :key="`el-${index}`"
            class="edge-label"
            :x="line.mx"
            :y="line.my - 4"
            text-anchor="middle"
          >
            {{ line.edge.type.replaceAll('_', ' ') }}
          </text>
        </g>

        <g
          v-for="node in nodes"
          :key="node.id"
          class="node"
          :class="{ 'is-selected': selectedId === node.id, 'is-dim': isDimNode(node) }"
          @pointerdown="startDrag($event, node)"
          @click.stop="selectNode(node, $event)"
          @pointerenter="hoverId = node.id"
          @pointerleave="hoverId = null"
        >
          <circle
            v-if="selectedId === node.id || hoverId === node.id"
            class="node-halo"
            :cx="node.x"
            :cy="node.y"
            :r="radiusOf(node) + 7"
            :fill="colorOf(node.type)"
          />
          <circle
            class="node-dot"
            :cx="node.x"
            :cy="node.y"
            :r="radiusOf(node)"
            :fill="colorOf(node.type)"
          />
          <text
            v-if="showLabel(node)"
            class="node-label"
            :x="node.x"
            :y="node.y + radiusOf(node) + (compact ? 10 : 14)"
            text-anchor="middle"
          >
            {{ shortLabel(node.label) }}
          </text>
        </g>
      </g>
    </svg>

    <p v-if="!compact && nodes.length" class="graph-hint">
      拖拽节点 · 滚轮缩放 · 点击查看关联
    </p>
  </div>
</template>

<style scoped>
.graph {
  position: relative;
  width: 100%;
  overflow: hidden;
  border-radius: inherit;
  background-image: radial-gradient(circle at 1px 1px, #dce8f8 1px, transparent 0);
  background-size: 22px 22px;
  background-position: -1px -1px;
}

.graph.is-compact {
  background-image: radial-gradient(circle at 1px 1px, #e2ebf9 1px, transparent 0);
  background-size: 17px 17px;
}

.graph-svg {
  display: block;
  width: 100%;
  height: 100%;
  touch-action: none;
  cursor: grab;
}

.graph-svg.is-panning {
  cursor: grabbing;
}

.edges line {
  stroke: #c6d8ef;
  stroke-width: 1.1;
  transition: opacity 0.18s ease, stroke 0.18s ease;
}

.edges line.is-active {
  stroke: #8fb4ef;
  stroke-width: 1.5;
}

.edges line.is-dim {
  opacity: 0.22;
}

.edge-label {
  font-size: 8.5px;
  font-weight: 550;
  letter-spacing: 0.06em;
  fill: #8598b5;
  paint-order: stroke;
  stroke: rgba(255, 255, 255, 0.95);
  stroke-width: 3px;
  pointer-events: none;
}

.node {
  cursor: grab;
  transition: opacity 0.18s ease;
}

.node:active {
  cursor: grabbing;
}

.node.is-dim {
  opacity: 0.28;
}

.node-dot {
  stroke: #fff;
  stroke-width: 2.4;
  transition: r 0.18s ease;
}

.node-halo {
  opacity: 0.14;
}

.node-label {
  font-size: 10.5px;
  font-weight: 500;
  fill: #596b89;
  paint-order: stroke;
  stroke: rgba(255, 255, 255, 0.92);
  stroke-width: 3.4px;
  stroke-linejoin: round;
  pointer-events: none;
  user-select: none;
}

.is-compact .node-label {
  font-size: 8.5px;
  stroke-width: 2.8px;
}

.graph-hint {
  position: absolute;
  left: 50%;
  bottom: 11px;
  transform: translateX(-50%);
  padding: 4px 10px;
  border: 1px solid var(--line);
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.82);
  color: #94a3ba;
  font-size: 10px;
  white-space: nowrap;
  backdrop-filter: blur(6px);
  pointer-events: none;
}
</style>
