"use client";

import { Search } from "lucide-react";
import type { OpportunityDetail } from "@/lib/types";
import { Breadcrumb, GoldButton, ProgressBar, SectionLabel } from "@/components/ui";
import { DataSourceNotice } from "@/components/ui/DataSourceNotice";
import type { DataSource } from "@/lib/data-source";

interface OpportunityDetailViewProps {
  opportunity: OpportunityDetail;
  dataSource?: DataSource;
}

export function OpportunityDetailView({
  opportunity,
  dataSource = "live",
}: OpportunityDetailViewProps) {
  return (
    <div className="animate-cyrise">
      <Breadcrumb
        items={[
          {
            label: "Scene Intelligence",
            href: opportunity.sceneId ? `/scene/${opportunity.sceneId}` : undefined,
          },
          { label: `${opportunity.category} Opportunity` },
        ]}
      />

      <DataSourceNotice source={dataSource} />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_344px]">
        <div className="flex flex-col gap-5">
          <div className="rounded bg-panel p-6">
            <div className="flex items-start justify-between">
              <div>
                <div className="font-mono text-[11px] text-gold">{opportunity.slug}</div>
                <h2 className="mt-2.5 text-[28px] font-bold leading-[1.1] tracking-[-0.02em] text-ink">
                  {opportunity.title}
                </h2>
                <div className="mt-2 font-mono text-xs text-ink2">
                  HORIZONS · S2E3 · Rooftop Reflection · {opportunity.timecode}
                </div>
              </div>
              <div className="flex-none text-right">
                <div className="text-[38px] font-bold leading-none tracking-[-0.02em] text-gold">
                  {opportunity.estimatedValue}
                </div>
                <div className="mt-0.5 text-[11px] text-ink3">Estimated value ⓘ</div>
              </div>
            </div>
            <p className="mt-5 text-[13.5px] leading-[1.6] text-pretty text-ink">
              {opportunity.description}
            </p>
          </div>

          <div className="grid grid-cols-1 rounded bg-panel px-6 py-0.5 sm:grid-cols-3">
            {opportunity.metrics.map((metric, i) => (
              <div
                key={metric.key}
                className={`py-[18px] ${i % 3 !== 0 ? "sm:border-l sm:border-line" : ""} ${
                  i > 2 ? "sm:border-t sm:border-line" : ""
                }`}
              >
                <div className="text-[11.5px] text-ink2">{metric.key}</div>
                <div
                  className={`mt-2 text-[22px] font-semibold leading-none tracking-[-0.4px] ${
                    metric.color === "green" ? "text-green" : "text-ink"
                  }`}
                >
                  {metric.value}
                </div>
                {metric.barPercent !== undefined && (
                  <div className="mt-2.5">
                    <ProgressBar
                      percent={metric.barPercent}
                      color={
                        metric.color === "green"
                          ? "var(--color-green)"
                          : "var(--color-gold)"
                      }
                    />
                  </div>
                )}
                {metric.note && (
                  <div className="mt-2 text-[10.5px] text-ink3">{metric.note}</div>
                )}
              </div>
            ))}
          </div>

          <div className="rounded bg-panel p-[22px]">
            <SectionLabel>CLICKHOUSE-DERIVED SIGNALS</SectionLabel>
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
              <SignalBlock
                label="Comparable demo deals"
                value={opportunity.clickhouseSignals.comparableDeals}
              />
              <SignalBlock
                label="Median cleared fee"
                value={opportunity.clickhouseSignals.medianFee}
              />
              <SignalBlock
                label="Category demand"
                value={opportunity.clickhouseSignals.categoryDemand}
                green
              />
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-[18px]">
          <div className="rounded bg-panel p-5">
            <SectionLabel>COMPATIBLE CATEGORIES</SectionLabel>
            <div className="mt-3.5 flex flex-wrap gap-2">
              {opportunity.compatibleCategories.map((cat, i) => (
                <span
                  key={cat}
                  className={`rounded px-[11px] py-[5px] text-xs ${
                    i === 0
                      ? "bg-[rgba(59,130,246,0.14)] font-semibold text-gold"
                      : "bg-well text-ink2"
                  }`}
                >
                  {cat}
                </span>
              ))}
            </div>
          </div>

          {opportunity.territories.length > 0 && (
            <div className="rounded bg-panel p-5">
              <SectionLabel>TERRITORY AVAILABILITY</SectionLabel>
              <div className="mt-3.5 flex flex-col gap-[11px]">
                {opportunity.territories.map((t) => (
                  <div
                    key={t.name}
                    className="flex justify-between text-[12.5px]"
                  >
                    <span className="text-ink">{t.name}</span>
                    <span
                      className={`font-semibold ${
                        t.status === "Cleared" ? "text-green" : "text-red"
                      }`}
                    >
                      {t.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="rounded bg-panel p-5">
            <p className="text-[12.5px] leading-[1.55] text-ink">
              Ready to see which campaigns fit? The Market Agent will query live
              inventory in ClickHouse.
            </p>
            <GoldButton href="/marketplace" className="mt-4 w-full rounded px-3 py-3">
              <Search size={15} strokeWidth={2.2} aria-hidden />
              Find Brand Matches
            </GoldButton>
          </div>
        </div>
      </div>
    </div>
  );
}

function SignalBlock({
  label,
  value,
  green,
}: {
  label: string;
  value: string;
  green?: boolean;
}) {
  return (
    <div>
      <div className="text-xs text-ink2">{label}</div>
      <div
        className={`mt-1 font-mono text-base ${green ? "text-green" : "text-ink"}`}
      >
        {value}
      </div>
    </div>
  );
}
