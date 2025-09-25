export type Holder = {
  address: string;
  balance: string; // big number as string
};

export type HoldersResponse = {
  items: Holder[];
  next_cursor: string | null;
};

export async function fetchHolders(
  cursor?: string,
  limit: number = 50
): Promise<HoldersResponse> {
  const url = new URL("http://localhost:8000/holders");
  if (cursor) url.searchParams.set("cursor", cursor);
  url.searchParams.set("limit", String(limit));

  const res = await fetch(url.toString(), {
    headers: { accept: "application/json" },
  });
  if (!res.ok) throw new Error("Failed to fetch holders");
  return res.json();
}
