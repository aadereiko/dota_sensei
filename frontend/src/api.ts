// All requests go to /api and are proxied to the backend on 8273 by Vite.

import type {
  MatchDetail,
  MatchSummary,
  Player,
  RecurringMistake,
  SyncResult,
} from "@/types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; database: string }>("/health"),

  config: () => request<{ default_account_id: number | null }>("/config"),

  player: (accountId: number) => request<Player>(`/players/${accountId}`),

  matches: (accountId: number, limit = 20) =>
    request<MatchSummary[]>(`/players/${accountId}/matches?limit=${limit}`),

  match: (accountId: number, matchId: number) =>
    request<MatchDetail>(`/players/${accountId}/matches/${matchId}`),

  recurring: (accountId: number) =>
    request<RecurringMistake[]>(`/players/${accountId}/insights/recurring`),

  sync: (accountId: number, limit = 20) =>
    request<SyncResult>("/sync", {
      method: "POST",
      body: JSON.stringify({ account_id: accountId, limit }),
    }),
};
