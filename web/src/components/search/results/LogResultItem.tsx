import { LogSearchResult } from "../../../hooks/useSearchResults";
import LogCard from "../../logs/LogCard";

interface LogResultItemProps {
  item: LogSearchResult;
}

export function LogResultItem({ item }: LogResultItemProps) {
  // Transform LogSearchResult to the format expected by LogCard
  const log = {
    id: item.id,
    trig_id: item.trig_id,
    user_id: item.user_id,
    trig_name: item.trig_name,
    user_name: item.user_name,
    date: item.date,
    time: item.time,
    condition: item.condition,
    comment: item.comment,
    score: item.score,
  };

  return <LogCard log={log} />;
}

