import { useInfiniteQuery } from "@tanstack/react-query";
import { fetchHolders, type HoldersResponse } from "../api/holders";

export function useHoldersInfinite(limit: number = 50) {
  return useInfiniteQuery<HoldersResponse, Error>({
    queryKey: ["holders", limit],
    queryFn: ({ pageParam }) =>
      fetchHolders(pageParam as string | undefined, limit),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    staleTime: 10_000,
    refetchOnWindowFocus: false,
  });
}
