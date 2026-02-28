/**
 * Intelligence Primitives — Shared UI building blocks for Intelligence Hub & Novel AI Lab.
 *
 * Consolidated from IntelligenceHub.tsx and NovelHub.tsx to eliminate
 * duplicated Chip / ResultBox / Spinner / CopyBtn definitions.
 */
import { useState, type ReactNode } from "react";
import { Loader2, Copy, Check } from "lucide-react";

/* ── Inline Loader ──────────────────────────────────────── */
export function Spinner() {
  return <Loader2 className="h-4 w-4 animate-spin" />;
}

/* ── Result Container ───────────────────────────────────── */
export function ResultBox({ children }: { children: ReactNode }) {
  return (
    <div className="mt-4 rounded-xl border border-border bg-muted/30 p-4 space-y-3 animate-fade-in">
      {children}
    </div>
  );
}

/* ── Status Chip ────────────────────────────────────────── */
const CHIP_VARIANTS = {
  purple: "bg-violet-500/10 text-violet-400 border-violet-500/20",
  blue:   "bg-blue-500/10 text-blue-400 border-blue-500/20",
  orange: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  green:  "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  red:    "bg-red-500/10 text-red-400 border-red-500/20",
  yellow: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
} as const;

export type ChipColor = keyof typeof CHIP_VARIANTS;

export function Chip({ text, color }: { text: string; color: ChipColor }) {
  return (
    <span
      className={`inline-flex items-center text-xs px-2 py-0.5 rounded-full border font-medium ${CHIP_VARIANTS[color]}`}
    >
      {text}
    </span>
  );
}

/* ── Copy-to-Clipboard Button ───────────────────────────── */
export function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      title="Copy to clipboard"
      onClick={handleCopy}
      className="text-muted-foreground hover:text-foreground transition-colors"
    >
      {copied ? (
        <Check className="h-3.5 w-3.5 text-emerald-400" />
      ) : (
        <Copy className="h-3.5 w-3.5" />
      )}
    </button>
  );
}
