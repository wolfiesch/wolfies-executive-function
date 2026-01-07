import { useCallback, useState } from 'react'

interface ConfettiPiece {
  id: number
  x: number
  color: string
  delay: number
}

/**
 * Hook to trigger confetti celebration animation
 * 
 * Uses CSS-only confetti for lightweight animation without external dependencies.
 * Returns a trigger function and the confetti element to render.
 */
export function useConfetti() {
  const [pieces, setPieces] = useState<ConfettiPiece[]>([])
  const [isActive, setIsActive] = useState(false)

  const colors = [
    'var(--color-accent-green)',
    'var(--color-accent-blue)',
    'var(--color-accent-purple)',
    'var(--color-accent-orange)',
    'var(--color-accent-yellow)',
  ]

  const trigger = useCallback(() => {
    // Generate random confetti pieces
    const newPieces: ConfettiPiece[] = Array.from({ length: 30 }, (_, i) => ({
      id: Date.now() + i,
      x: 20 + Math.random() * 60, // 20-80% horizontal spread
      color: colors[Math.floor(Math.random() * colors.length)],
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

  const ConfettiContainer = isActive ? (
    <div className="pointer-events-none fixed inset-0 z-[100] overflow-hidden">
      {pieces.map((piece) => (
        <div
          key={piece.id}
          className="absolute top-0 animate-confetti-fall"
          style={{
            left: `${piece.x}%`,
            animationDelay: `${piece.delay}s`
          }}
        >
          <div
            className="h-3 w-2 animate-confetti-spin"
            style={{
              backgroundColor: piece.color,
              borderRadius: '2px',
            }}
          />
        </div>
      ))}
    </div>
  ) : null

  return { trigger, ConfettiContainer }
}

export default useConfetti
