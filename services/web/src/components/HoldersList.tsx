import { useEffect, useMemo, useRef } from "react";
import { useHoldersInfinite } from "../hooks/useHoldersInfinite";

function addOneToIntegerString(intStr: string): string {
  let carry = 1;
  let result = "";
  for (let i = intStr.length - 1; i >= 0; i--) {
    const digit = intStr.charCodeAt(i) - 48; // '0' -> 48
    const sum = digit + carry;
    result = String(sum % 10) + result;
    carry = sum >= 10 ? 1 : 0;
  }
  if (carry) result = "1" + result;
  return result;
}

function groupThousands(intStr: string): string {
  return intStr.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function formatBalanceParts(value: string): {
  integer: string;
  fraction: string;
} {
  // value is base-18 integer string, return 2-decimal rounded parts without Number()
  if (!value) return { integer: "0", fraction: "00" };
  const len = value.length;
  let intRaw = len > 18 ? value.slice(0, len - 18) : "0";
  const fracRaw = value.padStart(19, "0").slice(-18);

  // Round to 2 decimals based on the 3rd fractional digit
  let firstTwo = fracRaw.slice(0, 2);
  const third = fracRaw.charCodeAt(2) - 48; // 0-9
  if (!Number.isNaN(third) && third >= 5) {
    const n = parseInt(firstTwo || "0", 10) + 1;
    if (n >= 100) {
      firstTwo = "00";
      intRaw = addOneToIntegerString(intRaw);
    } else {
      firstTwo = String(n).padStart(2, "0");
    }
  } else {
    firstTwo = (firstTwo || "0").padStart(2, "0");
  }

  return { integer: groupThousands(intRaw), fraction: firstTwo };
}

export function HoldersList() {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    status,
    error,
  } = useHoldersInfinite(50);

  const items = useMemo(
    () => data?.pages.flatMap((p) => p.items) ?? [],
    [data]
  );

  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const target = sentinelRef.current;
    if (!target) return;
    if (!hasNextPage) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const first = entries[0];
        if (first.isIntersecting) {
          fetchNextPage();
        }
      },
      { rootMargin: "200px" }
    );

    observer.observe(target);
    return () => observer.disconnect();
  }, [fetchNextPage, hasNextPage]);

  if (status === "pending") {
    return <div className="text-gray-500">Loading holders…</div>;
  }
  if (status === "error") {
    return (
      <div className="text-red-600">
        Failed to load holders: {(error as Error).message}
      </div>
    );
  }

  return (
    <div className="divide-y divide-gray-200 rounded-md border border-gray-200 bg-white">
      {items.map((h) => {
        const { integer, fraction } = formatBalanceParts(h.balance);
        return (
          <div
            key={h.address}
            className="flex items-center justify-between px-4 py-3"
          >
            <span className="font-mono text-sm text-gray-800">{h.address}</span>
            <span className="font-mono tabular-nums font-semibold text-gray-900 text-right min-w-[14ch] sm:min-w-[18ch] inline-flex items-baseline justify-end">
              <span className="text-right">{integer}</span>
              <span>.</span>
              <span>{fraction}</span>
            </span>
          </div>
        );
      })}
      <div ref={sentinelRef} />
      {isFetchingNextPage && (
        <div className="px-4 py-3 text-sm text-gray-500">Loading more…</div>
      )}
      {!hasNextPage && (
        <div className="px-4 py-3 text-sm text-gray-400">No more results</div>
      )}
    </div>
  );
}
