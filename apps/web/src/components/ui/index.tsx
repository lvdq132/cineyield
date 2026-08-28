import Link from "next/link";
import type { AnalysisStatus } from "@/lib/types";

const statusColors: Record<AnalysisStatus, string> = {
  Analyzed: "text-green",
  Analyzing: "text-gold",
  Queued: "text-ink3",
  Failed: "text-red",
};

interface StatusBadgeProps {
  status: AnalysisStatus;
  className?: string;
}

export function StatusBadge({ status, className = "" }: StatusBadgeProps) {
  return (
    <span
      className={`absolute right-3 top-3 rounded-[5px] bg-[rgba(13,11,9,0.62)] px-[9px] py-1 text-[9.5px] font-semibold uppercase tracking-[0.5px] backdrop-blur-[4px] ${statusColors[status]} ${className}`}
    >
      {status}
    </span>
  );
}

interface BreadcrumbProps {
  items: { label: string; href?: string }[];
}

export function Breadcrumb({ items }: BreadcrumbProps) {
  return (
    <div className="mb-4 flex items-center gap-2 font-mono text-[11.5px] text-ink3">
      {items.map((item, i) => (
        <span key={`${item.label}-${i}`} className="flex items-center gap-2">
          {i > 0 && <span>/</span>}
          {item.href ? (
            <Link href={item.href} className="cursor-pointer text-ink2 hover:text-gold">
              {item.label}
            </Link>
          ) : (
            <span className={i === items.length - 1 ? "text-gold" : "text-ink2"}>
              {item.label}
            </span>
          )}
        </span>
      ))}
    </div>
  );
}

interface NaturalnessChipProps {
  value: number;
}

export function NaturalnessChip({ value }: NaturalnessChipProps) {
  const style =
    value >= 85
      ? "bg-[rgba(126,190,150,0.14)] text-green"
      : value >= 70
        ? "bg-[rgba(203,160,78,0.14)] text-amber"
        : "bg-[#1e1e22] text-ink2";

  return (
    <span className={`inline-block rounded-[2px] px-2 py-0.5 font-mono text-[11.5px] ${style}`}>
      {value}
    </span>
  );
}

interface RightsChipProps {
  status: "Clear" | "Review";
}

export function RightsChip({ status }: RightsChipProps) {
  const style =
    status === "Clear"
      ? "bg-[rgba(126,190,150,0.12)] text-green"
      : "bg-[rgba(203,160,78,0.12)] text-amber";

  return (
    <span className={`inline-block rounded-[2px] px-2 py-0.5 text-[10px] font-semibold tracking-[0.4px] ${style}`}>
      {status}
    </span>
  );
}

interface ProgressBarProps {
  percent: number;
  color?: string;
  height?: string;
}

export function ProgressBar({
  percent,
  color = "var(--color-gold)",
  height = "3px",
}: ProgressBarProps) {
  return (
    <div className="overflow-hidden bg-[#1e1e22]" style={{ height }}>
      <div className="h-full" style={{ width: `${percent}%`, background: color }} />
    </div>
  );
}

interface SectionLabelProps {
  children: React.ReactNode;
}

export function SectionLabel({ children }: SectionLabelProps) {
  return (
    <div className="text-[10.5px] font-semibold tracking-[1.4px] text-ink2">
      {children}
    </div>
  );
}

interface PrimaryButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  href?: string;
  className?: string;
  type?: "button" | "submit";
}

export function PrimaryButton({
  children,
  onClick,
  href,
  className = "",
  type = "button",
}: PrimaryButtonProps) {
  const styles =
    "inline-flex h-[46px] cursor-pointer items-center justify-between gap-8 border border-gold bg-gold px-5 text-[11px] font-bold uppercase tracking-[0.05em] text-[#111214] transition-colors hover:bg-transparent hover:text-gold";

  if (href) {
    return (
      <Link href={href} className={`${styles} ${className}`}>
        {children}
      </Link>
    );
  }

  return (
    <button type={type} onClick={onClick} className={`${styles} ${className}`}>
      {children}
    </button>
  );
}

interface SecondaryButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  href?: string;
  className?: string;
}

export function SecondaryButton({
  children,
  onClick,
  href,
  className = "",
}: SecondaryButtonProps) {
  const styles =
    "inline-flex h-[46px] cursor-pointer items-center justify-between gap-8 border border-line2 bg-transparent px-5 text-[11px] font-bold uppercase tracking-[0.05em] text-ink transition-colors hover:border-gold hover:text-gold";

  if (href) {
    return (
      <Link href={href} className={`${styles} ${className}`}>
        {children}
      </Link>
    );
  }

  return (
    <button type="button" onClick={onClick} className={`${styles} ${className}`}>
      {children}
    </button>
  );
}

interface GoldButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  href?: string;
  className?: string;
  disabled?: boolean;
}

export function GoldButton({
  children,
  onClick,
  href,
  className = "",
  disabled = false,
}: GoldButtonProps) {
  const styles =
    "inline-flex cursor-pointer items-center justify-center gap-2 border-none bg-gold text-[13.5px] font-semibold text-white transition-[background] hover:bg-gold-hi disabled:cursor-default disabled:opacity-100";

  if (href && !disabled) {
    return (
      <Link href={href} className={`${styles} ${className}`}>
        {children}
      </Link>
    );
  }

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`${styles} ${className}`}
    >
      {children}
    </button>
  );
}
