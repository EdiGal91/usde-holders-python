import { useStatusQuery } from "../hooks/useStatusQuery";

export function Header() {
  console.log("Header render");

  const { data, isLoading, isError } = useStatusQuery();

  return (
    <header className="sticky top-0 z-50 w-full border-b border-gray-200 bg-white/90 backdrop-blur supports-[backdrop-filter]:bg-white/60">
      <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between">
        <div className="text-lg font-semibold text-gray-900">
          USDe Holdings Tracker
        </div>
        <div className="flex items-center gap-3 text-sm">
          {isLoading ? (
            <span className="text-gray-500">Loading status…</span>
          ) : isError ? (
            <span className="text-red-600">Failed to load status</span>
          ) : (
            <span className="text-gray-700">
              Last synced block:{" "}
              <span className="font-mono font-bold">
                {data?.last_block ?? 0}
              </span>
            </span>
          )}
        </div>
      </div>
    </header>
  );
}
