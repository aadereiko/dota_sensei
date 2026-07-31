// All requests go to /api and are proxied to the backend on 8273 by Vite.

import type {
  CurrentUser,
  Hero,
  Item,
  MatchDetail,
  MatchFull,
  MatchImportResult,
  ParseStatus,
  MatchSummary,
  Player,
  RecurringMistake,
  SyncResult,
} from "@/types";

/** Thrown for 401s so callers can tell "signed out" from a real failure. */
export class UnauthorizedError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    // Send the session cookie.
    credentials: "same-origin",
    ...init,
  });
  if (response.status === 401) throw new UnauthorizedError("not signed in");
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }
  return response.json() as Promise<T>;
}

/** Full-page navigation, not fetch — Steam has to render its own login page. */
export const STEAM_LOGIN_URL = "/api/auth/steam/login";

export const api = {
  health: () => request<{ status: string; database: string }>("/health"),

  config: () => request<{ default_account_id: number | null }>("/config"),

  heroes: () => request<Hero[]>("/heroes"),

  items: () => request<Item[]>("/items"),

  me: () => request<CurrentUser>("/auth/me"),

  logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),

  player: (accountId: number) => request<Player>(`/players/${accountId}`),

  matches: (accountId: number, limit = 20) =>
    request<MatchSummary[]>(`/players/${accountId}/matches?limit=${limit}`),

  requestParse: (matchId: number) =>
    request<ParseStatus>(`/matches/${matchId}/parse`, { method: "POST" }),

  checkParse: (matchId: number, jobId: number) =>
    request<ParseStatus>(`/matches/${matchId}/parse/${jobId}`),

  /** The whole match: both teams, inventories, advantage series. */
  fullMatch: (matchId: number) => request<MatchFull>(`/matches/${matchId}`),

  match: (accountId: number, matchId: number) =>
    request<MatchDetail>(`/players/${accountId}/matches/${matchId}`),

  recurring: (accountId: number) =>
    request<RecurringMistake[]>(`/players/${accountId}/insights/recurring`),

  /**
   * Analyse a single match by id. Pass playerSlot on a second call when the
   * first comes back unresolved.
   */
  importMatch: (matchId: number, accountId: number | null, playerSlot?: number) =>
    request<MatchImportResult>("/matches/import", {
      method: "POST",
      body: JSON.stringify({
        match_id: matchId,
        account_id: accountId,
        player_slot: playerSlot ?? null,
      }),
    }),

  /** Omit accountId to sync whoever is signed in. */
  sync: (accountId: number | null, limit = 20) =>
    request<SyncResult>("/sync", {
      method: "POST",
      body: JSON.stringify({ account_id: accountId, limit }),
    }),
};
