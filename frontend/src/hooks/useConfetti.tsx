import { useCallback, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface ConfettiPiece {
  id: number
  x: number
  color: string
  delay: number
}

const COLORS = [
  'var(--color-accent-green)',
  'var(--color-accent-blue)',
  'var(--color-accent-purple)',
  'var(--color-accent-orange)',
  'var(--color-accent-yellow)',
]

/**
 * Hook to trigger confetti celebration animation
 * 
 * Uses CSS-only confetti for lightweight animation without external dependencies.
 * Returns a trigger function and the confetti element to render.
 */
export function useConfetti() {
  const [pieces, setPieces] = useState<ConfettiPiece[]>([])
  const [isActive, setIsActive] = useState(false)


  const trigger = useCallback(() => {
    // Generate random confetti pieces
    const newPieces: ConfettiPiece[] = Array.from({ length: 30 }, (_, i) => ({
      id: Date.now() + i,
      x: 20 + Math.random() * 60, // 20-80% horizontal spread
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      delay: Math.random() * 0.3,
    }))

    setPieces(newPieces)
    setIsActive(true)

    // Clean up after animation
    setTimeout(() => {
      setIsActive(false)
      setPieces([])
    }, 2000)
  }, [])

  const ConfettiContainer = (
    <div className="pointer-events-none fixed inset-0 z-[100] overflow-hidden">
      <AnimatePresence>
        {isActive && pieces.map((piece) => (
          <motion.div
            key={piece.id}
            initial={{ y: -20, opacity: 1, x: `${piece.x}%`, rotate: 0 }}
            animate={{
              y: '100vh',
              opacity: 0,
              rotate: 720
            }}
            transition={{
              duration: 2,
              ease: "easeOut",
              delay: piece.delay
            }}
            className="absolute top-0"
          >
            <motion.div
              animate={{
                rotateX: [0, 90, 180, 270, 360],
                rotateY: [0, 45, 90, 135, 180]
              }}
              transition={{
                duration: 0.6,
                repeat: Infinity,
                ease: "linear"
              }}
              style={{ backgroundColor: piece.color }}
              className="h-3 w-2 rounded-[2px]"
            />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )

  return { trigger, ConfettiContainer }
}

export default useConfetti
