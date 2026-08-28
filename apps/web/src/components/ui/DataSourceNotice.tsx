import type { DataSource } from "@/lib/data-source";

interface DataSourceNoticeProps {
  source: DataSource;
}

/**
 * One-line notice shown only when a page is displaying fixture data instead
 * of a live fetch. Renders nothing for "live" — that's the common case and
 * it stays clean. The two fallback cases read differently on purpose: an
 * unconfigured API is a legitimate offline demo, a failed one is degraded.
 */
export function DataSourceNotice({ source }: DataSourceNoticeProps) {
  if (source === "live") return null;

  if (source === "offline") {
    return (
      <div className="mb-5 border-y border-line bg-well px-[13px] py-[11px] font-mono text-[10px] text-ink2">
        ⓘ Offline demo mode — showing sample data, no API configured.
      </div>
    );
  }

  return (
    <div className="mb-5 border-y border-line border-l-[3px] border-l-amber bg-panel px-[13px] py-[11px] font-mono text-[10px] text-amber">
      ⓘ Live API unreachable — showing sample data, not current results.
    </div>
  );
}
