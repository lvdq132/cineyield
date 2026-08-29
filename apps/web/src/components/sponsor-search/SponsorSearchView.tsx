import Link from "next/link";
import { ArrowRight, Check, Search, ShieldCheck } from "lucide-react";
import { Breadcrumb } from "@/components/ui";

export interface SponsorSceneResult {
  opportunity_id: string;
  scene_id: string;
  asset_id: string;
  asset_title: string;
  asset_subtitle?: string | null;
  episode?: string | null;
  scene_name: string;
  scene_summary: string;
  mood?: string | null;
  narrative_weight?: string | null;
  category: string;
  object_label: string;
  timecode_start?: string | null;
  timecode_end?: string | null;
  screen_time_seconds: number;
  naturalness_score: number;
  brand_safety_score: number;
  rights_status: string;
  estimated_value_usd: number;
  fit_score: number;
  rationale: string;
  marketplace_path: string;
}

export interface SponsorSearchData {
  query: {
    category: string;
    objective: string;
    budget: number;
    territory: string;
  };
  total_scanned: number;
  qualified_count: number;
  results: SponsorSceneResult[];
  provenance: {
    retrieval: string;
    scene_intelligence: string;
    ranking: string;
  };
}

const categories = [
  "Consumer Audio",
  "Mobile Devices",
  "Home / Beverage",
  "Consumer Electronics",
  "Wearables",
];

const objectives = [
  "Launch a product",
  "Build consideration",
  "Own a cultural moment",
];

const budgets = [
  { value: "50000", label: "$25K–$75K" },
  { value: "125000", label: "$75K–$150K" },
  { value: "250000", label: "$150K+" },
];

function money(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function SponsorSearchView({ data }: { data: SponsorSearchData }) {
  const query = data.query;

  return (
    <div className="animate-cyrise">
      <Breadcrumb items={[{ label: "Library", href: "/library" }, { label: "Sponsor Finder" }]} />

      <header className="grid gap-7 border-b border-line pb-8 lg:grid-cols-[1fr_440px] lg:items-end">
        <div>
          <span className="font-mono text-[10px] font-bold uppercase tracking-[0.14em] text-gold">
            Live inventory search / ClickHouse
          </span>
          <h1 className="mt-4 max-w-[820px] text-[clamp(44px,6vw,82px)] font-medium leading-[0.88] tracking-[-0.065em] text-ink">
            Find the scene your campaign belongs in.
          </h1>
        </div>
        <p className="m-0 text-[16px] leading-[1.65] text-ink2">
          Turn a sponsor brief into ranked, producer-controlled inventory. Every result comes from an analyzed scene—not a fabricated recommendation.
        </p>
      </header>

      <form action="/sponsor-search" method="get" className="my-7 grid border-y border-line md:grid-cols-2 xl:grid-cols-[1.2fr_1.2fr_1fr_.7fr_auto]">
        <SearchField label="Category">
          <select name="category" defaultValue={query.category} className="w-full bg-transparent text-[15px] font-semibold text-ink outline-none">
            {categories.map((value) => <option key={value} value={value} className="bg-canvas">{value}</option>)}
          </select>
        </SearchField>
        <SearchField label="Campaign objective">
          <select name="objective" defaultValue={query.objective} className="w-full bg-transparent text-[15px] font-semibold text-ink outline-none">
            {objectives.map((value) => <option key={value} value={value} className="bg-canvas">{value}</option>)}
          </select>
        </SearchField>
        <SearchField label="Working budget">
          <select name="budget" defaultValue={String(Math.round(query.budget))} className="w-full bg-transparent text-[15px] font-semibold text-ink outline-none">
            {budgets.map((item) => <option key={item.value} value={item.value} className="bg-canvas">{item.label}</option>)}
          </select>
        </SearchField>
        <SearchField label="Territory">
          <select name="territory" defaultValue={query.territory} className="w-full bg-transparent text-[15px] font-semibold text-ink outline-none">
            <option value="US" className="bg-canvas">United States</option>
            <option value="CA" className="bg-canvas">Canada</option>
            <option value="GB" className="bg-canvas">United Kingdom</option>
          </select>
        </SearchField>
        <button type="submit" className="flex min-h-[86px] cursor-pointer items-center justify-center gap-3 bg-gold px-7 text-[12px] font-bold uppercase tracking-[0.08em] text-[#101112] transition-colors hover:bg-ink hover:text-canvas">
          <Search size={16} strokeWidth={2.2} aria-hidden />
          Run search
        </button>
      </form>

      <div className="mb-7 flex flex-wrap items-center justify-between gap-4 border-b border-line pb-5">
        <div>
          <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink3">Qualified inventory</div>
          <div className="mt-1 text-[24px] font-semibold tracking-[-0.035em] text-ink">
            {data.qualified_count} real {data.qualified_count === 1 ? "scene" : "scenes"} for {query.category}
          </div>
        </div>
        <div className="flex flex-wrap gap-x-5 gap-y-2 font-mono text-[10px] uppercase tracking-[0.09em] text-ink3">
          <span className="inline-flex items-center gap-2"><Check size={13} className="text-green" />{data.provenance.retrieval}</span>
          <span className="inline-flex items-center gap-2"><Check size={13} className="text-green" />{data.provenance.scene_intelligence}</span>
          <span className="inline-flex items-center gap-2"><Check size={13} className="text-green" />{data.provenance.ranking}</span>
        </div>
      </div>

      {data.results.length ? (
        <div className="divide-y divide-line border-y border-line">
          {data.results.map((result, index) => (
            <article key={result.opportunity_id} className="grid gap-6 py-7 lg:grid-cols-[72px_1.25fr_.85fr_190px] lg:items-center">
              <div className="font-mono text-[13px] text-ink3">{String(index + 1).padStart(2, "0")}</div>
              <div>
                <div className="font-mono text-[9px] font-bold uppercase tracking-[0.13em] text-gold">
                  {result.asset_title}{result.episode ? ` · ${result.episode}` : ""}
                </div>
                <h2 className="mt-2 text-[clamp(27px,3vw,40px)] font-medium leading-none tracking-[-0.045em] text-ink">{result.scene_name}</h2>
                <p className="mb-0 mt-3 max-w-[660px] text-[14px] leading-[1.55] text-ink2">{result.rationale}</p>
              </div>
              <dl className="grid grid-cols-2 gap-x-5 gap-y-4 border-l border-line pl-6">
                <Metric label="Placement" value={result.object_label} />
                <Metric label="Screen time" value={`${result.screen_time_seconds}s`} />
                <Metric label="Naturalness" value={`${Math.round(result.naturalness_score)}%`} />
                <Metric label="Modeled value" value={money(result.estimated_value_usd)} />
              </dl>
              <div className="flex flex-col items-start lg:items-end">
                <div className="flex items-end gap-2">
                  <strong className="font-mono text-[42px] font-medium leading-none text-gold">{Math.round(result.fit_score)}</strong>
                  <span className="pb-1 text-[11px] text-ink3">brief fit</span>
                </div>
                <div className="mt-2 inline-flex items-center gap-2 text-[11px] text-green"><ShieldCheck size={14} />Rights {result.rights_status}</div>
                <Link href={`${result.marketplace_path}&objective=${encodeURIComponent(query.objective)}&budget=${query.budget}&territory=${query.territory}`} className="mt-5 inline-flex items-center gap-2 border-b border-gold pb-1 text-[12px] font-bold uppercase tracking-[0.06em] text-ink hover:text-gold">
                  Match sponsors <ArrowRight size={14} />
                </Link>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="border-y border-line py-16">
          <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-gold">No qualified inventory</div>
          <h2 className="mt-3 text-[36px] font-medium tracking-[-0.045em] text-ink">No scene currently clears this brief.</h2>
          <p className="max-w-[620px] text-[15px] leading-[1.6] text-ink2">Try another category or analyze more footage. CineYield will not invent a match to fill the screen.</p>
        </div>
      )}
    </div>
  );
}

function SearchField({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="flex min-h-[86px] flex-col justify-center border-b border-line px-5 py-4 md:border-b-0 md:border-r"><span className="mb-2 font-mono text-[9px] font-bold uppercase tracking-[0.12em] text-ink3">{label}</span>{children}</label>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div><dt className="font-mono text-[9px] uppercase tracking-[0.1em] text-ink3">{label}</dt><dd className="m-0 mt-1 text-[13px] font-semibold text-ink">{value}</dd></div>;
}
