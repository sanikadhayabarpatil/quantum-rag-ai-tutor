"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useState } from "react"
import { Home, MessageSquare, FileText, Menu, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { QubitLogo } from "@/components/qubit-logo"
import { Button } from "@/components/ui/button"

const navItems = [
  { href: "/", label: "Home", icon: Home },
  { href: "/ask", label: "Ask the Tutor", icon: MessageSquare },
  { href: "/summarize", label: "Summarize", icon: FileText },
]

export function Sidebar() {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)

  return (
    <>
      {/* Mobile menu button */}
      <Button
        variant="ghost"
        size="icon"
        className="fixed top-4 left-4 z-50 md:hidden bg-card/80 backdrop-blur border border-border"
        onClick={() => setOpen(!open)}
        aria-label="Toggle menu"
      >
        {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </Button>

      {/* Backdrop on mobile */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-background/80 backdrop-blur-sm md:hidden"
          onClick={() => setOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          "fixed md:sticky top-0 left-0 z-40 h-screen w-64 shrink-0",
          "bg-sidebar border-r border-sidebar-border",
          "flex flex-col transition-transform duration-300",
          open ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        )}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-6 border-b border-sidebar-border">
          <QubitLogo size={36} />
          <div className="flex flex-col">
            <span className="text-base font-bold tracking-tight text-foreground">
              QuantumMind
            </span>
            <span className="text-[10px] uppercase tracking-widest text-primary">
              Quantum AI
            </span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-6 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const active =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href)
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-all",
                  active
                    ? "bg-primary/10 text-primary border border-primary/30 glow-primary"
                    : "text-muted-foreground hover:text-foreground hover:bg-sidebar-accent",
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{item.label}</span>
                {active && (
                  <span className="ml-auto h-2 w-2 rounded-full bg-primary shadow-[0_0_8px_#00d4ff]" />
                )}
              </Link>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-sidebar-border">
          <p className="text-xs text-muted-foreground leading-relaxed">
            <span className="text-primary">RAG + GPT</span> powered learning for
            the quantum age.
          </p>
        </div>
      </aside>
    </>
  )
}
