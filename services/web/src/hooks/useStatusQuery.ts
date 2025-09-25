import { useQuery } from "@tanstack/react-query";
import { fetchStatus, type StatusResponse } from "../api/status";

export function useStatusQuery() {
  return useQuery<StatusResponse, Error>({
    queryKey: ["status"],
    queryFn: fetchStatus,
    refetchInterval: 5000,
    staleTime: 3000,
  });
}
