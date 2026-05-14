"use client"

import { useEffect, useState } from "react"
import { Upload, FileText, Download, Sparkles, X } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import {
  fetchPublications,
  getApiErrorMessage,
  summarizeStored,
  summarizeUpload,
  type Publication,
  type SummaryResponse,
} from "@/lib/api"
import { cn } from "@/lib/utils"

function getDocLabel(p: Publication): string {
  return p.document_title || p.file_name
}

function getDocId(p: Publication): string {
  return p.file_name
}

function toLines(value: string | string[] | undefined): string[] {
  if (!value) return []
  if (Array.isArray(value)) return value.filter(Boolean)
  // Split paragraphs / bullet points
  return value
    .split(/\n+|(?:^|\s)[•\-\*]\s+/g)
    .map((s) => s.trim())
    .filter(Boolean)
}

interface SummarySection {
  label: string
  key: keyof SummaryResponse
}

const SECTIONS: SummarySection[] = [
  { label: "Overview", key: "overview" },
  { label: "Key Concepts", key: "key_concepts" },
  { label: "Important Details", key: "important_details" },
  { label: "Main Takeaways", key: "main_takeaways" },
]

export default function SummarizePage() {
  const [publications, setPublications] = useState<Publication[]>([])
  const [tab, setTab] = useState("upload")

  // Upload tab state
  const [file, setFile] = useState<File | null>(null)
  const [uploadTopic, setUploadTopic] = useState("")
  const [dragOver, setDragOver] = useState(false)

  // Stored tab state
  const [selectedDoc, setSelectedDoc] = useState<string>("")
  const [storedTopic, setStoredTopic] = useState("")

  const [loading, setLoading] = useState(false)
  const [summary, setSummary] = useState<SummaryResponse | null>(null)

  useEffect(() => {
    fetchPublications()
      .then(setPublications)
      .catch((err) => {
        console.log("[v0] Could not load publications:", getApiErrorMessage(err))
      })
  }, [])

  async function handleUploadSummarize() {
    // Hard guard: only run when the upload tab is active.
    if (tab !== "upload") return
    if (!file) {
      toast.error("Please select a PDF file first.")
      return
    }
    setLoading(true)
    setSummary(null)
    try {
      // Multipart POST to /summarize-pdf/
      const res = await summarizeUpload(file, uploadTopic.trim())
      setSummary(res)
    } catch (err) {
      toast.error(getApiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function handleStoredSummarize() {
    // Hard guard: only run when the stored tab is active.
    if (tab !== "stored") return
    if (!selectedDoc) {
      toast.error("Please select a document.")
      return
    }
    setLoading(true)
    setSummary(null)
    try {
      const res = await summarizeStored(selectedDoc, storedTopic.trim())
      setSummary(res)
    } catch (err) {
      toast.error(getApiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragOver(false)
    const dropped = e.dataTransfer.files?.[0]
    if (dropped) {
      if (!dropped.name.toLowerCase().endsWith(".pdf")) {
        toast.error("Please drop a PDF file.")
        return
      }
      setFile(dropped)
      setSummary(null)
    }
  }

  function handleDownload() {
    if (!summary) return
    const lines: string[] = ["QuantumMind Summary", "===================", ""]
    SECTIONS.forEach((s) => {
      const content = summary[s.key]
      if (!content) return
      lines.push(s.label.toUpperCase())
      lines.push("-".repeat(s.label.length))
      const items = toLines(content as string | string[])
      if (items.length > 1) {
        items.forEach((it) => lines.push(`- ${it}`))
      } else {
        lines.push(items[0] || String(content))
      }
      lines.push("")
    })
    if (summary.summary && !SECTIONS.some((s) => summary[s.key])) {
      lines.push(String(summary.summary))
    }
    const blob = new Blob([lines.join("\n")], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "quantummind-summary.txt"
    a.click()
    URL.revokeObjectURL(url)
  }

  const hasStructuredSummary =
    !!summary && SECTIONS.some((s) => summary[s.key])

  return (
    <div className="min-h-screen px-4 md:px-6 py-8 md:py-12">
      <div className="max-w-4xl mx-auto flex flex-col gap-8">
        {/* Header */}
        <div className="pl-12 md:pl-0">
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight">
            Summarize
          </h1>
          <p className="text-sm md:text-base text-muted-foreground mt-1">
            Upload a PDF or pick a stored document to generate a structured
            summary.
          </p>
        </div>

        {/* Tabs */}
        <Tabs
          value={tab}
          onValueChange={(value) => {
            setTab(value)
            setSummary(null)
          }}
          className="w-full"
        >
          <TabsList className="bg-card border border-border p-1 h-auto">
            <TabsTrigger
              value="upload"
              className="data-[state=active]:bg-primary/15 data-[state=active]:text-primary data-[state=active]:border data-[state=active]:border-primary/30 px-4 py-2"
            >
              <Upload className="h-4 w-4 mr-2" />
              Upload PDF
            </TabsTrigger>
            <TabsTrigger
              value="stored"
              className="data-[state=active]:bg-primary/15 data-[state=active]:text-primary data-[state=active]:border data-[state=active]:border-primary/30 px-4 py-2"
            >
              <FileText className="h-4 w-4 mr-2" />
              Stored Documents
            </TabsTrigger>
          </TabsList>

          <TabsContent value="upload" className="mt-6">
            <Card className="bg-card/60 border-border p-5 md:p-6 flex flex-col gap-5">
              {/* Dropzone */}
              <div
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragOver(true)
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                className={cn(
                  "relative rounded-lg border-2 border-dashed p-8 md:p-12 text-center transition-all",
                  dragOver
                    ? "border-primary bg-primary/5 glow-primary"
                    : "border-border bg-input/30 hover:border-primary/40",
                )}
              >
                <input
                  type="file"
                  accept="application/pdf,.pdf"
                  onChange={(e) => {
                    setFile(e.target.files?.[0] || null)
                    setSummary(null)
                  }}
                  className="absolute inset-0 opacity-0 cursor-pointer"
                  aria-label="Upload PDF"
                />
                <div className="flex flex-col items-center gap-3 pointer-events-none">
                  <div className="h-12 w-12 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center">
                    <Upload className="h-5 w-5 text-primary" />
                  </div>
                  {file ? (
                    <div className="flex flex-col gap-1">
                      <p className="text-sm font-medium text-foreground">
                        {file.name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {(file.size / 1024 / 1024).toFixed(2)} MB · click or drop
                        to replace
                      </p>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-1">
                      <p className="text-sm font-medium text-foreground">
                        Drop your PDF here or click to browse
                      </p>
                      <p className="text-xs text-muted-foreground">
                        PDF files only
                      </p>
                    </div>
                  )}
                </div>
                {file && (
                  <Button
                    variant="ghost"
                    size="icon"
                    type="button"
                    className="absolute top-2 right-2 h-7 w-7 z-10"
                    onClick={(e) => {
                      e.stopPropagation()
                      setFile(null)
                      setSummary(null)
                    }}
                    aria-label="Remove file"
                  >
                    <X className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>

              <div className="flex flex-col gap-2">
                <Label htmlFor="upload-topic" className="text-sm">
                  Topic or chapter{" "}
                  <span className="text-muted-foreground font-normal">
                    (optional)
                  </span>
                </Label>
                <Input
                  id="upload-topic"
                  value={uploadTopic}
                  onChange={(e) => setUploadTopic(e.target.value)}
                  placeholder="e.g. Quantum entanglement"
                  className="bg-input border-border focus-visible:ring-primary"
                />
              </div>

              <Button
                onClick={handleUploadSummarize}
                disabled={loading || !file}
                size="lg"
                className="bg-primary text-primary-foreground hover:bg-primary/90 glow-primary self-start"
              >
                <Sparkles className="h-4 w-4 mr-2" />
                Summarize
              </Button>
            </Card>
          </TabsContent>

          <TabsContent value="stored" className="mt-6">
            <Card className="bg-card/60 border-border p-5 md:p-6 flex flex-col gap-5">
              <div className="flex flex-col gap-2">
                <Label htmlFor="stored-doc" className="text-sm">
                  Document
                </Label>
                <Select
                  value={selectedDoc}
                  onValueChange={(value) => {
                    setSelectedDoc(value)
                    setSummary(null)
                  }}
                >
                  <SelectTrigger
                    id="stored-doc"
                    className="bg-input border-border"
                  >
                    <SelectValue
                      placeholder={
                        publications.length === 0
                          ? "No stored documents available"
                          : "Select a stored document"
                      }
                    />
                  </SelectTrigger>
                  <SelectContent className="bg-popover border-border">
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

              <div className="flex flex-col gap-2">
                <Label htmlFor="stored-topic" className="text-sm">
                  Chapter or topic{" "}
                  <span className="text-muted-foreground font-normal">
                    (optional)
                  </span>
                </Label>
                <Input
                  id="stored-topic"
                  value={storedTopic}
                  onChange={(e) => setStoredTopic(e.target.value)}
                  placeholder="e.g. Chapter 3: Quantum Gates"
                  className="bg-input border-border focus-visible:ring-primary"
                />
              </div>

              <Button
                onClick={handleStoredSummarize}
                disabled={loading || !selectedDoc}
                size="lg"
                className="bg-primary text-primary-foreground hover:bg-primary/90 glow-primary self-start"
              >
                <Sparkles className="h-4 w-4 mr-2" />
                Summarize
              </Button>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Result */}
        {loading && (
          <Card className="bg-card border-border p-8 flex items-center justify-center gap-3">
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full rounded-full bg-primary opacity-75 animate-ping" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary" />
            </span>
            <span className="text-sm text-muted-foreground">
              Generating summary...
            </span>
          </Card>
        )}

        {summary && !loading && (
          <Card className="bg-card border-border p-5 md:p-6 flex flex-col gap-5 glow-primary">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-md bg-primary/10 border border-primary/30 flex items-center justify-center">
                  <Sparkles className="h-4 w-4 text-primary" />
                </div>
                <h2 className="text-lg md:text-xl font-semibold">Summary</h2>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownload}
                className="border-primary/40 text-primary hover:bg-primary/10 bg-transparent"
              >
                <Download className="h-3.5 w-3.5 mr-2" />
                Download as text
              </Button>
            </div>

            {hasStructuredSummary ? (
              <div className="flex flex-col gap-5">
                {SECTIONS.map((s) => {
                  const raw = summary[s.key]
                  if (!raw) return null
                  const items = toLines(raw as string | string[])
                  const isList = Array.isArray(raw) || items.length > 1
                  return (
                    <section key={s.label} className="flex flex-col gap-2">
                      <h3 className="text-xs font-semibold uppercase tracking-wider text-primary">
                        {s.label}
                      </h3>
                      {isList ? (
                        <ul className="flex flex-col gap-1.5 pl-1">
                          {items.map((item, i) => (
                            <li
                              key={i}
                              className="text-sm leading-relaxed text-foreground flex gap-2"
                            >
                              <span className="text-primary mt-1 shrink-0">
                                •
                              </span>
                              <span>{item}</span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-sm leading-relaxed text-foreground whitespace-pre-wrap">
                          {items[0] || String(raw)}
                        </p>
                      )}
                    </section>
                  )
                })}
              </div>
            ) : (
              <p className="text-sm leading-relaxed text-foreground whitespace-pre-wrap">
                {summary.summary
                  ? String(summary.summary)
                  : JSON.stringify(summary, null, 2)}
              </p>
            )}
          </Card>
        )}
      </div>
    </div>
  )
}
