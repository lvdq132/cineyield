import { SponsorSearchView, type SponsorSearchData } from "@/components/sponsor-search/SponsorSearchView";
import { IS_CONTEST_MODE as CONTEST_MODE } from "@/lib/contest-mode";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

interface SponsorSearchPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

function valueOf(value: string | string[] | undefined, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

export default async function SponsorSearchPage({ searchParams }: SponsorSearchPageProps) {
  const params = await searchParams;
  const category = valueOf(params.category, "Consumer Audio");
  const objective = valueOf(params.objective, "Launch a product");
  const territory = valueOf(params.territory, "US");
  const budgetCandidate = Number(valueOf(params.budget, "250000"));
  const budget = Number.isFinite(budgetCandidate) && budgetCandidate > 0 ? budgetCandidate : 250000;

  const query = new URLSearchParams({
    category,
    objective,
    territory,
    budget: String(budget),
  });

  if (!API_BASE) {
    throw new Error("Sponsor search requires NEXT_PUBLIC_API_URL");
  }

  const response = await fetch(`${API_BASE}/api/v1/sponsor-search?${query.toString()}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    if (CONTEST_MODE) throw new Error(`Sponsor search API returned ${response.status}`);
    throw new Error("Sponsor search is temporarily unavailable");
  }

  const data = await response.json() as SponsorSearchData;
  return <SponsorSearchView data={data} />;
}
