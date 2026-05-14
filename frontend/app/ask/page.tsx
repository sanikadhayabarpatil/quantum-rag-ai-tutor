"use client"

import { useEffect, useRef, useState } from "react"
import { Send, Copy, Check, ExternalLink, Sparkles } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Card } from "@/components/ui/card"
import {
  askQuestion,
  fetchPublications,
  getApiErrorMessage,
  type Publication,
  type RelatedPaper,
} from "@/lib/api"
import { cn } from "@/lib/utils"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  relatedPapers?: RelatedPaper[]
}

function getDocLabel(p: Publication): string {
  return p.document_title || p.file_name
}

function getDocId(p: Publication): string {
  return p.file_name
}

export default function AskPage() {
  const [publications, setPublications] = useState<Publication[]>([])
  const [contextId, setContextId] = useState<string>("general")
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchPublications()
      .then(setPublications)
      .catch((err) => {
        // Soft fail — user can still ask general questions
        console.log("[v0] Could not load publications:", getApiErrorMessage(err))
      })
  }, [])

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    })
  }, [messages, loading])

  async function handleSend() {
    const query = input.trim()
    if (!query || loading) return

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: query,
    }
    setMessages((m) => [...m, userMsg])
    setInput("")
    setLoading(true)

    try {
      const res = await askQuestion(query, contextId)
      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: res.answer || "No answer returned.",
        relatedPapers: res.related_papers || [],
      }
      setMessages((m) => [...m, assistantMsg])
    } catch (err) {
      toast.error(getApiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function handleCopy(id: string, text: string) {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 1500)
    } catch {
      toast.error("Could not copy to clipboard")
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <header className="border-b border-border bg-card/40 backdrop-blur px-6 py-4 md:py-5">
        <div className="max-w-4xl mx-auto flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
          <div className="pl-12 md:pl-0">
            <h1 className="text-xl md:text-2xl font-bold tracking-tight">
              Ask the Tutor
            </h1>
            <p className="text-sm text-muted-foreground">
              Quantum computing Q&amp;A grounded in your documents.
            </p>
          </div>
          <Select value={contextId} onValueChange={setContextId}>
            <SelectTrigger className="w-full sm:w-[260px] bg-input border-border">
              <SelectValue placeholder="Select context" />
            </SelectTrigger>
            <SelectContent className="bg-popover border-border">
              <SelectItem value="general">General Question</SelectItem>
              {publications.map((p) => {
                const id = getDocId(p)
                if (!id) return null
                return (
                  <SelectItem key={id} value={id}>
                    {getDocLabel(p)}
                  </SelectItem>
                )
              })}
            </SelectContent>
          </Select>
        </div>
      </header>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 md:px-6 py-6">
        <div className="max-w-4xl mx-auto flex flex-col gap-4">
          {messages.length === 0 && !loading && (
            <div className="flex-1 flex flex-col items-center justify-center text-center py-20 gap-4">
              <div className="h-16 w-16 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center glow-primary">
                <Sparkles className="h-7 w-7 text-primary" />
              </div>
              <div className="flex flex-col gap-1">
                <p className="text-lg font-medium text-foreground">
                  Ask me anything about quantum computing
                </p>
                <p className="text-sm text-muted-foreground">
                  Try: &quot;Explain superposition in simple terms&quot;
                </p>
              </div>
            </div>
          )}

          {messages.map((msg) =>
            msg.role === "user" ? (
              <div key={msg.id} className="flex justify-end">
                <div className="max-w-[85%] md:max-w-[75%] rounded-2xl rounded-tr-sm bg-primary text-primary-foreground px-4 py-3 text-sm leading-relaxed glow-primary">
                  {msg.content}
                </div>
              </div>
            ) : (
              <div key={msg.id} className="flex justify-start">
                <Card className="max-w-[92%] md:max-w-[85%] bg-card border-border p-4 md:p-5 relative">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute top-2 right-2 h-7 w-7 text-muted-foreground hover:text-primary"
                    onClick={() => handleCopy(msg.id, msg.content)}
                    aria-label="Copy answer"
                  >
                    {copiedId === msg.id ? (
                      <Check className="h-3.5 w-3.5" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )}
                  </Button>
                  <div className="pr-8 text-sm leading-relaxed text-foreground whitespace-pre-wrap">
                    {msg.content}
                  </div>

                  {msg.relatedPapers && msg.relatedPapers.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-border">
                      <p className="text-xs font-semibold uppercase tracking-wider text-primary mb-2">
                        Related Papers
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {msg.relatedPapers.map((p, i) => {
                          const href = p.url || p.link
                          const chipClass = cn(
                            "inline-flex items-center gap-1.5 max-w-full rounded-full px-3 py-1 text-xs",
                            "bg-primary/10 text-primary border border-primary/30",
                            "hover:bg-primary/20 transition-colors",
                          )
                          return href ? (
                            <a
                              key={i}
                              href={href}
                              target="_blank"
                              rel="noopener noreferrer"
                              className={chipClass}
                            >
                              <span className="truncate max-w-[280px]">
                                {p.title}
                              </span>
                              <ExternalLink className="h-3 w-3 shrink-0" />
                            </a>
                          ) : (
                            <span key={i} className={chipClass}>
                              <span className="truncate max-w-[280px]">
                                {p.title}
                              </span>
                            </span>
                          )
                        })}
                      </div>
                    </div>
                  )}
                </Card>
              </div>
            ),
          )}

          {loading && (
            <div className="flex justify-start">
              <Card className="bg-card border-border px-4 py-3 flex items-center gap-3">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="absolute inline-flex h-full w-full rounded-full bg-primary opacity-75 animate-ping" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary" />
                </span>
                <span className="text-sm text-muted-foreground">Thinking...</span>
              </Card>
            </div>
          )}
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-border bg-card/40 backdrop-blur px-4 md:px-6 py-4">
        <div className="max-w-4xl mx-auto flex gap-2 items-end">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask a question about quantum computing..."
            rows={1}
            className="min-h-[48px] max-h-32 resize-none bg-input border-border focus-visible:ring-primary"
          />
          <Button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            size="lg"
            className="bg-primary text-primary-foreground hover:bg-primary/90 glow-primary shrink-0 h-12"
            aria-label="Send"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
