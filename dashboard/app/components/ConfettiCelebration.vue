<script setup lang="ts">
interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  color: string
  size: number
  rotation: number
  rotationSpeed: number
  shape: 'rect' | 'circle'
}

const props = withDefaults(defineProps<{
  particleCount?: number
  duration?: number
  colors?: string[]
}>(), {
  particleCount: 150,
  duration: 4000,
  colors: () => ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4']
})

const emit = defineEmits<{
  complete: []
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const isActive = ref(false)
let animationId: number | null = null
let particles: Particle[] = []

function createParticle(): Particle {
  const angle = Math.random() * Math.PI * 2
  const velocity = 8 + Math.random() * 8
  return {
    x: window.innerWidth / 2,
    y: window.innerHeight / 2,
    vx: Math.cos(angle) * velocity * (0.5 + Math.random()),
    vy: Math.sin(angle) * velocity * (0.5 + Math.random()) - 4,
    color: props.colors[Math.floor(Math.random() * props.colors.length)],
    size: 6 + Math.random() * 8,
    rotation: Math.random() * Math.PI * 2,
    rotationSpeed: (Math.random() - 0.5) * 0.3,
    shape: Math.random() > 0.5 ? 'rect' : 'circle'
  }
}

function animate(ctx: CanvasRenderingContext2D, startTime: number) {
  const elapsed = Date.now() - startTime
  const progress = Math.min(elapsed / props.duration, 1)
  
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height)
  
  const gravity = 0.15
  const friction = 0.99
  const fadeStart = 0.7
  const alpha = progress > fadeStart ? 1 - (progress - fadeStart) / (1 - fadeStart) : 1

  for (const p of particles) {
    p.vy += gravity
    p.vx *= friction
    p.vy *= friction
    p.x += p.vx
    p.y += p.vy
    p.rotation += p.rotationSpeed

    ctx.save()
    ctx.translate(p.x, p.y)
    ctx.rotate(p.rotation)
    ctx.globalAlpha = alpha
    ctx.fillStyle = p.color

    if (p.shape === 'rect') {
      ctx.fillRect(-p.size / 2, -p.size / 4, p.size, p.size / 2)
    } else {
      ctx.beginPath()
      ctx.arc(0, 0, p.size / 2, 0, Math.PI * 2)
      ctx.fill()
    }
    ctx.restore()
  }

  if (progress < 1) {
    animationId = requestAnimationFrame(() => animate(ctx, startTime))
  } else {
    stop()
  }
}

function start() {
  if (isActive.value || !canvasRef.value) return

  const canvas = canvasRef.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  canvas.width = window.innerWidth
  canvas.height = window.innerHeight
  
  isActive.value = true
  particles = Array.from({ length: props.particleCount }, createParticle)
  
  animate(ctx, Date.now())
}

function stop() {
  if (animationId) {
    cancelAnimationFrame(animationId)
    animationId = null
  }
  isActive.value = false
  particles = []
  emit('complete')
}

onUnmounted(() => {
  if (animationId) cancelAnimationFrame(animationId)
})

defineExpose({ start, stop })
</script>

<template>
  <Teleport to="body">
    <canvas
      ref="canvasRef"
      class="fixed inset-0 pointer-events-none z-50"
      :class="{ 'opacity-0': !isActive }"
    />
  </Teleport>
</template>
