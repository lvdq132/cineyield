/**
 * Classifies *why* a page is about to render fixture data instead of a live
 * fetch result, so the UI can say so instead of staying silent.
 *
 *  - "live": a configured API call actually produced the data on screen.
 *  - "offline": NEXT_PUBLIC_API_URL isn't set. Intended offline demo mode —
 *    entirely legitimate, reads quietly.
 *  - "degraded": the API was configured but the call failed or errored, so
 *    fixtures are standing in for data the deploy expected to be live. Reads
 *    more prominently — this is the state worth flagging to a judge.
 *
 * In contest mode (see contest-mode.ts) a configured-but-failing call throws
 * instead of falling back, so "degraded" is never actually reached there —
 * this only classifies the fallback path that mode disables.
 */
export type DataSource = "live" | "offline" | "degraded";

export function dataSourceFor(apiConfigured: boolean, usedLiveData: boolean): DataSource {
  if (usedLiveData) return "live";
  return apiConfigured ? "degraded" : "offline";
}
