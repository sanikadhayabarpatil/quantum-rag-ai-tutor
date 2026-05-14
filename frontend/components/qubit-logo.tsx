import { cn } from "@/lib/utils"

interface QubitLogoProps {
  size?: number
  className?: string
  animated?: boolean
}

export function QubitLogo({ size = 64, className, animated = true }: QubitLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn(className)}
      role="img"
      aria-label="QuantumMind atom logo"
    >
      {/* Orbit 1 */}
      <g className={animated ? "atom-orbit-1" : undefined} style={{ transformOrigin: "50px 50px" }}>
        <ellipse
          cx="50"
          cy="50"
          rx="40"
          ry="14"
          stroke="#00d4ff"
          strokeWidth="1.5"
          opacity="0.7"
        />
        <circle cx="90" cy="50" r="3" fill="#00d4ff" />
      </g>

      {/* Orbit 2 */}
      <g
        className={animated ? "atom-orbit-2" : undefined}
        style={{ transformOrigin: "50px 50px", transform: "rotate(60deg)" }}
      >
        <ellipse
          cx="50"
          cy="50"
          rx="40"
          ry="14"
          stroke="#38bdf8"
          strokeWidth="1.5"
          opacity="0.6"
        />
        <circle cx="10" cy="50" r="2.5" fill="#38bdf8" />
      </g>

      {/* Orbit 3 */}
      <g
        className={animated ? "atom-orbit-3" : undefined}
        style={{ transformOrigin: "50px 50px", transform: "rotate(120deg)" }}
      >
        <ellipse
          cx="50"
          cy="50"
          rx="40"
          ry="14"
          stroke="#818cf8"
          strokeWidth="1.5"
          opacity="0.5"
        />
        <circle cx="90" cy="50" r="2.5" fill="#818cf8" />
      </g>

      {/* Nucleus */}
      <circle
        cx="50"
        cy="50"
        r="6"
        fill="#00d4ff"
        className={animated ? "atom-nucleus" : undefined}
      />
      <circle cx="50" cy="50" r="3" fill="#ffffff" opacity="0.9" />
    </svg>
  )
}
