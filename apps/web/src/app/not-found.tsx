import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-[56vh] max-w-[440px] animate-cyrise flex-col items-start justify-center">
      <div className="font-mono text-xs tracking-[1px] text-ink3">NOT FOUND</div>
      <h2 className="mt-3 text-[32px] font-bold leading-[1.05] tracking-[-0.02em] text-ink">
        Page not found
      </h2>
      <p className="mt-3 text-sm leading-[1.55] text-pretty text-ink2">
        This surface is not part of the demo path. Try Library → Scene Intelligence →
        Marketplace → Deal → Analytics.
      </p>
      <Link
        href="/library"
        className="mt-[22px] rounded border border-line2 bg-transparent px-5 py-[11px] text-[13px] font-semibold text-gold transition-colors hover:border-gold hover:text-gold-hi"
      >
        ← Back to Studio Library
      </Link>
    </div>
  );
}
