export type StatusResponse = {
  last_block: number;
};

export async function fetchStatus(): Promise<StatusResponse> {
  const res = await fetch("http://localhost:8000/status", {
    headers: { accept: "application/json" },
  });
  if (!res.ok) throw new Error("Failed to fetch status");
  return res.json();
}
