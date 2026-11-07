<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

import { setPetEnabled, ui } from '../store'

const messages = [
  '今天也只读该读的文献。',
  '先跑字符初筛，再交给知识图谱。',
  '二轮审阅交给我，你负责精读。',
  '别忘了导出 BibTeX 哦。',
  '点我一下，换个提醒～',
]

const index = ref(0)
const bubble = ref(false)
const hopping = ref(false)
const petRef = ref(null)
const pos = ref(null)

let drag = null
let moved = false

function clamp(x, y) {
  const el = petRef.value
  const width = el?.offsetWidth || 120
  const height = el?.offsetHeight || 208
  return {
    x: Math.min(Math.max(8, x), Math.max(8, window.innerWidth - width - 8)),
    y: Math.min(Math.max(8, y), Math.max(8, window.innerHeight - height - 8)),
  }
}

function defaultPosition() {
  const el = petRef.value
  const width = el?.offsetWidth || 120
  const height = el?.offsetHeight || 208
  pos.value = {
    x: window.innerWidth - width - 16,
    y: window.innerHeight - height - 6,
  }
}

function restorePosition() {
  try {
    const saved = JSON.parse(localStorage.getItem('le-pet-pos') || 'null')
    if (saved && Number.isFinite(saved.x) && Number.isFinite(saved.y)) {
      pos.value = clamp(saved.x, saved.y)
      return
    }
  } catch {
    // ignore broken localStorage
  }
  defaultPosition()
}

function onResize() {
  if (pos.value) pos.value = clamp(pos.value.x, pos.value.y)
}

function startDrag(event) {
  if (event.button !== undefined && event.button !== 0) return
  const el = petRef.value
  if (!el) return

  const rect = el.getBoundingClientRect()
  drag = {
    startX: event.clientX,
    startY: event.clientY,
    originX: rect.left,
    originY: rect.top,
    pointerId: event.pointerId,
  }
  moved = false
  bubble.value = false

  el.setPointerCapture?.(event.pointerId)
  window.addEventListener('pointermove', onDrag)
  window.addEventListener('pointerup', endDrag)
}

function onDrag(event) {
  if (!drag) return
  const dx = event.clientX - drag.startX
  const dy = event.clientY - drag.startY
  if (Math.abs(dx) > 4 || Math.abs(dy) > 4) moved = true
  pos.value = clamp(drag.originX + dx, drag.originY + dy)
}

function endDrag(event) {
  window.removeEventListener('pointermove', onDrag)
  window.removeEventListener('pointerup', endDrag)
  petRef.value?.releasePointerCapture?.(drag?.pointerId)

  if (drag) {
    if (moved) {
      localStorage.setItem('le-pet-pos', JSON.stringify(pos.value))
    } else {
      poke()
    }
  }
  drag = null
}

function poke() {
  index.value = (index.value + 1) % messages.length
  bubble.value = true
  hopping.value = true
  window.setTimeout(() => {
    hopping.value = false
  }, 620)
}

function hideBubble() {
  bubble.value = false
}

function disable() {
  setPetEnabled(false)
}

onMounted(() => {
  nextTick(restorePosition)
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('pointermove', onDrag)
  window.removeEventListener('pointerup', endDrag)
})
</script>

<template>
  <div
    v-if="ui.petEnabled"
    ref="petRef"
    class="pet"
    :style="
      pos
        ? {
            left: `${pos.x}px`,
            top: `${pos.y}px`,
            right: 'auto',
            bottom: 'auto',
          }
        : undefined
    "
  >
    <Transition name="bubble">
      <div v-if="bubble" class="bubble">
        <span>{{ messages[index] }}</span>
        <button class="bubble-close" type="button" aria-label="收起提醒" @click="hideBubble">
          ×
        </button>
      </div>
    </Transition>

    <button
      class="pet-body"
      :class="{ 'is-hopping': hopping }"
      type="button"
      aria-label="拖动桌宠，点击互动"
      @pointerdown.prevent="startDrag"
    >
      <span class="glow" aria-hidden="true" />
      <span class="shadow" aria-hidden="true" />
      <img
        class="mascot"
        src="/mascot/solve.png"
        srcset="/mascot/solve.png 1x, /mascot/solve@2x.png 2x"
        alt="桌面小人"
        draggable="false"
      />
      <span class="spark s1" aria-hidden="true" />
      <span class="spark s2" aria-hidden="true" />
      <span class="spark s3" aria-hidden="true" />
    </button>

    <button class="pet-off" type="button" title="关闭桌宠" aria-label="关闭桌宠" @click="disable">
      ×
    </button>
  </div>
</template>

<style scoped>
.pet {
  position: fixed;
  right: 16px;
  bottom: 6px;
  z-index: 45;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  pointer-events: none;
}

.pet-body,
.bubble,
.pet-off {
  pointer-events: auto;
}

.pet-body {
  position: relative;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: grab;
  touch-action: none;
  animation: float 4.2s ease-in-out infinite;
  transition: transform 0.18s ease;
}

.pet-body:active {
  cursor: grabbing;
}

.pet-body:hover {
  animation-play-state: paused;
}

.mascot {
  position: relative;
  z-index: 2;
  display: block;
  height: 208px;
  width: auto;
  user-select: none;
  -webkit-user-drag: none;
  transform-origin: 50% 92%;
  will-change: transform;
  image-rendering: auto;
}

.is-hopping .mascot {
  animation: hop 0.6s cubic-bezier(0.3, 1.4, 0.5, 1);
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-9px);
  }
}


@keyframes hop {
  0% {
    transform: translateY(0) scale(1);
  }
  35% {
    transform: translateY(-22px) scale(1.03, 0.97);
  }
  65% {
    transform: translateY(0) scale(0.98, 1.02);
  }
  100% {
    transform: translateY(0) scale(1);
  }
}

/* 背后的柔光 */
.glow {
  position: absolute;
  inset: 8% -12% 6% -12%;
  z-index: 1;
  border-radius: 50%;
  background: radial-gradient(
    circle,
    rgba(143, 190, 255, 0.34) 0%,
    rgba(180, 160, 255, 0.18) 42%,
    transparent 70%
  );
  filter: blur(10px);
  animation: glow-pulse 4.2s ease-in-out infinite;
}

@keyframes glow-pulse {
  0%,
  100% {
    opacity: 0.55;
    transform: scale(1);
  }
  50% {
    opacity: 0.95;
    transform: scale(1.06);
  }
}

.shadow {
  position: absolute;
  left: 50%;
  bottom: -2px;
  z-index: 0;
  width: 74%;
  height: 12px;
  border-radius: 50%;
  background: rgba(20, 30, 60, 0.2);
  filter: blur(5px);
  transform: translateX(-50%);
  animation: shadow-pulse 4.2s ease-in-out infinite;
}

@keyframes shadow-pulse {
  0%,
  100% {
    transform: translateX(-50%) scaleX(1);
    opacity: 0.55;
  }
  50% {
    transform: translateX(-50%) scaleX(0.86);
    opacity: 0.3;
  }
}

/* 粒子 */
.spark {
  position: absolute;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  opacity: 0;
  z-index: 3;
  animation: twinkle 3.2s ease-in-out infinite;
}

.s1 {
  top: 18%;
  left: 2%;
  background: #9fd0ff;
  animation-delay: 0.2s;
}

.s2 {
  top: 6%;
  right: 6%;
  background: #d8b4ff;
  animation-delay: 1.1s;
}

.s3 {
  bottom: 20%;
  right: 0;
  background: #ffd166;
  animation-delay: 2s;
}

@keyframes twinkle {
  0%,
  100% {
    opacity: 0;
    transform: scale(0.4);
  }
  45% {
    opacity: 1;
    transform: scale(1);
  }
}

/* 气泡：绝对定位，不参与拖拽尺寸计算 */
.bubble {
  position: absolute;
  right: 0;
  bottom: calc(100% + 8px);
  max-width: min(214px, calc(100vw - 32px));
  padding: 10px 30px 10px 13px;
  border-radius: 14px;
  border: 1px solid var(--line-2);
  background: var(--surface);
  color: var(--ink-soft);
  font-size: 11.5px;
  line-height: 1.6;
  box-shadow: var(--shadow-md);
  animation: bubble-in 0.24s cubic-bezier(0.22, 1, 0.36, 1);
}

.bubble::after {
  content: '';
  position: absolute;
  right: 34px;
  bottom: -6px;
  width: 10px;
  height: 10px;
  background: var(--surface);
  border-right: 1px solid var(--line-2);
  border-bottom: 1px solid var(--line-2);
  transform: rotate(45deg);
}

@keyframes bubble-in {
  from {
    opacity: 0;
    transform: translateY(6px) scale(0.96);
  }
}

.bubble-close {
  position: absolute;
  top: 4px;
  right: 6px;
  width: 18px;
  height: 18px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--faint);
  font-size: 13px;
  line-height: 1;
}

.bubble-close:hover {
  background: var(--surface-soft);
  color: var(--ink-soft);
}

.pet-off {
  position: absolute;
  top: -2px;
  right: 2px;
  width: 20px;
  height: 20px;
  display: grid;
  place-items: center;
  border: 1px solid var(--line);
  border-radius: 50%;
  background: var(--surface);
  color: var(--faint);
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.16s ease;
}

.pet:hover .pet-off {
  opacity: 1;
}

.pet-off:hover {
  color: var(--red);
  border-color: var(--red);
}

.bubble-enter-active,
.bubble-leave-active {
  transition: opacity 0.16s ease, transform 0.16s ease;
}

.bubble-enter-from,
.bubble-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

@media (max-width: 760px) {
  .pet {
    right: 8px;
    bottom: 4px;
  }

  .mascot {
    height: 168px;
  }

  .bubble {
    max-width: 180px;
    font-size: 10.5px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .pet-body,
  .mascot,
  .glow,
  .shadow,
  .spark {
    animation: none;
  }
}
</style>
