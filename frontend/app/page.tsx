import Link from "next/link"
import { Sparkles, FileText, BookOpen, ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { QubitLogo } from "@/components/qubit-logo"

const features = [
  {
    icon: Sparkles,
    title: "RAG-Powered Answers",
    description:
      "Retrieval-augmented responses grounded in your indexed documents and trusted sources.",
  },
  {
    icon: FileText,
    title: "Document Summarization",
    description:
      "Turn dense PDFs into structured overviews, key concepts, details, and takeaways.",
  },
  {
    icon: BookOpen,
    title: "Research Papers",
    description:
      "Surface related papers alongside every answer to deepen your understanding.",
  },
]

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Hero */}
      <section className="flex-1 flex items-center justify-center px-6 py-20 md:py-28">
        <div className="max-w-4xl w-full flex flex-col items-center text-center gap-8">
          {/* Animated logo */}
          <div className="relative">
            <div className="absolute inset-0 blur-3xl bg-primary/20 rounded-full" />
            <QubitLogo size={120} className="relative" />
          </div>

          {/* Title */}
          <div className="flex flex-col gap-4">
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-balance text-glow">
              QuantumMind
            </h1>
            <p className="text-lg md:text-xl text-primary tracking-wide">
              AI-powered learning for the quantum age
            </p>
          </div>

          {/* Description */}
          <p className="max-w-2xl text-base md:text-lg text-muted-foreground leading-relaxed text-pretty">
            Ask questions, summarize documents, and explore research papers —
            all powered by{" "}
            <span className="text-foreground font-medium">RAG</span> and{" "}
            <span className="text-foreground font-medium">GPT</span>.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row gap-3 mt-2">
            <Button
              asChild
              size="lg"
              className="bg-primary text-primary-foreground hover:bg-primary/90 glow-primary-strong font-medium"
            >
              <Link href="/ask">
                Ask the Tutor
                <ArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="border-primary/40 text-foreground hover:bg-primary/10 hover:text-primary bg-transparent"
            >
              <Link href="/summarize">Summarize a Document</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="px-6 pb-20 md:pb-28">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {features.map((feature) => {
              const Icon = feature.icon
              return (
                <Card
                  key={feature.title}
                  className="bg-card/60 border-border backdrop-blur p-6 flex flex-col gap-4 transition-all hover:border-primary/40 hover:glow-primary group"
                >
                  <div className="h-12 w-12 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                    <Icon className="h-6 w-6 text-primary" />
                  </div>
                  <div className="flex flex-col gap-2">
                    <h3 className="text-lg font-semibold text-foreground">
                      {feature.title}
                    </h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      {feature.description}
                    </p>
                  </div>
                </Card>
              )
            })}
          </div>
        </div>
      </section>
    </div>
  )
}
