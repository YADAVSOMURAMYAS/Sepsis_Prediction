import { useEffect, useRef } from 'react'
import { useTheme } from '../context/ThemeContext'

interface Particle {
  x: number; y: number; vx: number; vy: number
  r: number; opacity: number; pulse: number
}

export default function ParticleBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const { theme } = useTheme()
  const particlesRef = useRef<Particle[]>([])
  const rafRef = useRef<number>(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')!
    let W = window.innerWidth, H = window.innerHeight

    const resize = () => {
      W = window.innerWidth; H = window.innerHeight
      canvas.width = W; canvas.height = H
    }
    resize()
    window.addEventListener('resize', resize)

    // Init particles
    const N = Math.min(80, Math.floor(W * H / 16000))
    particlesRef.current = Array.from({ length: N }, () => ({
      x: Math.random() * W, y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      r: Math.random() * 1.5 + 0.5,
      opacity: Math.random() * 0.5 + 0.1,
      pulse: Math.random() * Math.PI * 2,
    }))

    const CYAN_DARK  = [6, 182, 212]
    const BLUE_DARK  = [59, 130, 246]
    const CYAN_LIGHT = [2, 132, 199]
    const BLUE_LIGHT = [37, 99, 235]

    const draw = () => {
      ctx.clearRect(0, 0, W, H)
      const [cr, cg, cb] = theme === 'dark' ? CYAN_DARK : CYAN_LIGHT
      const [br, bg, bb] = theme === 'dark' ? BLUE_DARK : BLUE_LIGHT

      particlesRef.current.forEach(p => {
        p.pulse += 0.015
        p.x += p.vx; p.y += p.vy
        if (p.x < 0) p.x = W; if (p.x > W) p.x = 0
        if (p.y < 0) p.y = H; if (p.y > H) p.y = 0
        const op = p.opacity * (0.7 + 0.3 * Math.sin(p.pulse))
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${cr},${cg},${cb},${op})`
        ctx.fill()
      })

      // Draw connections
      const pts = particlesRef.current
      for (let i = 0; i < pts.length; i++) {
        for (let j = i + 1; j < pts.length; j++) {
          const dx = pts[i].x - pts[j].x
          const dy = pts[i].y - pts[j].y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist < 120) {
            const alpha = (1 - dist / 120) * 0.12
            ctx.beginPath()
            ctx.moveTo(pts[i].x, pts[i].y)
            ctx.lineTo(pts[j].x, pts[j].y)
            ctx.strokeStyle = `rgba(${br},${bg},${bb},${alpha})`
            ctx.lineWidth = 0.8
            ctx.stroke()
          }
        }
      }

      rafRef.current = requestAnimationFrame(draw)
    }

    draw()
    return () => {
      window.removeEventListener('resize', resize)
      cancelAnimationFrame(rafRef.current)
    }
  }, [theme])

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed', inset: 0, zIndex: 0,
        pointerEvents: 'none', opacity: 0.6,
      }}
    />
  )
}
