// Mirrors backend/app/schemas.py. Keep the two in sync by hand for now; if this
// starts drifting, generate from the OpenAPI schema at /openapi.json instead.

export type Severity = "info" | "warn" | "critical";

export interface Insight {
  rule_key: string;
  severity: Severity;
  title: string;
  detail: string;
  metrics: Record<string, number | string | null> | null;
}

export interface MatchSummary {
  match_id: number;
  start_time: string;
  duration_seconds: number;
  hero_id: number;
  hero_name: string | null;
  hero_icon_url: string | null;
  won: boolean;
  kills: number | null;
  deaths: number | null;
  assists: number | null;
  gold_per_min: number | null;
  xp_per_min: number | null;
  /** Unparsed matches have no lane_role / timeline, so fewer rules can run. */
  is_parsed: boolean;
  insight_count: number;
  worst_severity: Severity | null;
}

export interface MatchDetail extends MatchSummary {
  last_hits: number | null;
  denies: number | null;
  net_worth: number | null;
  hero_damage: number | null;
  tower_damage: number | null;
  hero_healing: number | null;
  obs_placed: number | null;
  sen_placed: number | null;
  lane_role: number | null;
  benchmarks: Record<string, unknown> | null;
  item_timings: Record<string, unknown> | null;
  insights: Insight[];
}

export interface CurrentUser {
  account_id: number;
  /** 17 digits — a string because it exceeds Number.MAX_SAFE_INTEGER. */
  steam_id64: string;
  persona_name: string | null;
  avatar_url: string | null;
  last_synced_at: string | null;
}

export interface Player {
  account_id: number;
  persona_name: string | null;
  avatar_url: string | null;
  rank_tier: number | null;
  estimate_mmr: number | null;
  last_synced_at: string | null;
}

export interface RecurringMistake {
  rule_key: string;
  title: string;
  occurrences: number;
  severity: Severity;
}

export interface MatchSlot {
  player_slot: number;
  is_radiant: boolean;
  hero_id: number;
  hero_name: string | null;
  hero_icon_url: string | null;
  account_id: number | null;
  won: boolean;
  kills: number | null;
  deaths: number | null;
  assists: number | null;
  gold_per_min: number | null;
  net_worth: number | null;
}

export interface MatchImportResult {
  match_id: number;
  /** False when we couldn't tell which player is you — pick from candidates. */
  resolved: boolean;
  is_parsed: boolean;
  insights_created: number;
  candidates: MatchSlot[];
}

export interface SyncResult {
  account_id: number;
  matches_seen: number;
  matches_ingested: number;
  insights_created: number;
}
