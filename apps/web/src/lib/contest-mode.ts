/**
 * Contest mode guard — works on both server and client components.
 *
 * Activate via environment:
 *   CINEYIELD_MODE=contest          (backend)
 *   NEXT_PUBLIC_CINEYIELD_MODE=contest  (frontend)
 *
 * Legacy alias still accepted:
 *   NEXT_PUBLIC_CONTEST_MODE=true
 *
 * In contest mode:
 *   - All API calls are mandatory (Gemini, GCS, ClickHouse, mcp-clickhouse)
 *   - Fixture fallback is forbidden
 *   - Any integration failure surfaces as an error page
 */
export const IS_CONTEST_MODE =
  process.env.NEXT_PUBLIC_CINEYIELD_MODE === "contest" ||
  process.env.NEXT_PUBLIC_CONTEST_MODE === "true";
