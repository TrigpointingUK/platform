import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { LogSearchResult } from "../../../hooks/useSearchResults";
import { highlightText } from "../../../lib/textHighlight";
import Card from "../../ui/Card";
import StarRating from "../../ui/StarRating";

interface LogResultItemProps {
  item: LogSearchResult;
}

// Helper function to get condition icon and label
function getConditionInfo(code: string): { icon: string; label: string } {
  const conditions: Record<string, { icon: string; label: string }> = {
    Z: { icon: "c_unknown.png", label: "Not Logged" },
    N: { icon: "c_possiblymissing.png", label: "Couldn't Find" },
    G: { icon: "c_good.png", label: "Good" },
    S: { icon: "c_slightlydamaged.png", label: "Slightly Damaged" },
    C: { icon: "c_slightlydamaged.png", label: "Converted" },
    D: { icon: "c_damaged.png", label: "Damaged" },
    R: { icon: "c_toppled.png", label: "Remains" },
    T: { icon: "c_toppled.png", label: "Toppled" },
    M: { icon: "c_toppled.png", label: "Moved" },
    Q: { icon: "c_possiblymissing.png", label: "Possibly Missing" },
    X: { icon: "c_definitelymissing.png", label: "Destroyed" },
    V: { icon: "c_unreachablebutvisible.png", label: "Unreachable but Visible" },
    P: { icon: "c_unknown.png", label: "Inaccessible" },
    U: { icon: "c_unknown.png", label: "Unknown" },
    "-": { icon: "c_nolog.png", label: "Not Visited" },
  };
  return conditions[code] || { icon: "c_unknown.png", label: code };
}

export function LogResultItem({ item }: LogResultItemProps) {
  const [searchParams] = useSearchParams();
  const query = searchParams.get("q") || "";
  const navigate = useNavigate();

  const conditionInfo = getConditionInfo(item.condition);
  const formattedDate = new Date(item.date).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  const formattedTrigId = `TP${item.trig_id.toString().padStart(4, "0")}`;

  const handleCardClick = () => {
    navigate(`/logs/${item.id}`);
  };

  return (
    <Card
      className="hover:shadow-lg transition-shadow cursor-pointer"
      onClick={handleCardClick}
    >
      <div className="flex flex-col gap-3">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <Link
              to={`/trigs/${item.trig_id}`}
              className="text-lg font-semibold text-trig-green-600 hover:text-trig-green-700 hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              {formattedTrigId}
              {item.trig_name && (
                <>
                  <span className="text-gray-400 mx-2">·</span>
                  <span className="font-normal text-gray-700">
                    {item.trig_name}
                  </span>
                </>
              )}
            </Link>
            <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600">
              <span>
                by{" "}
                {item.user_name ? (
                  <Link
                    to={`/profile/${item.user_id}`}
                    className="text-trig-green-600 hover:underline font-semibold text-base"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {item.user_name}
                  </Link>
                ) : (
                  <Link
                    to={`/profile/${item.user_id}`}
                    className="text-trig-green-600 hover:underline font-semibold text-base"
                    onClick={(e) => e.stopPropagation()}
                  >
                    User #{item.user_id}
                  </Link>
                )}
              </span>
              <span className="text-gray-400">·</span>
              {/* Condition Icon */}
              <img 
                src={`/icons/conditions/${conditionInfo.icon}`}
                alt={conditionInfo.label}
                title={conditionInfo.label}
                className="w-4 h-4"
              />
              <StarRating
                rating={item.score / 2}
                size="sm"
                title={`${item.score}/10`}
              />
              <span className="text-gray-400">·</span>
              <span className="text-gray-700">{formattedDate}</span>
              {item.time && item.time !== "12:00:00" && (
                <span className="text-gray-500 text-xs">{item.time}</span>
              )}
            </div>
          </div>
        </div>

        {/* Comment with highlighting */}
        {item.comment && (
          <div className="flex-[2] min-w-0">
            <p className="text-gray-700 text-sm leading-relaxed">
              {highlightText(item.comment, query)}
            </p>
          </div>
        )}
      </div>
    </Card>
  );
}

