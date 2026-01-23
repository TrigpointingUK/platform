import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { LogSearchResult } from "../../../hooks/useSearchResults";
import { highlightText } from "../../../lib/textHighlight";
import { useConditionInfo } from "../../../hooks/useConditionInfo";
import Card from "../../ui/Card";
import StarRating from "../../ui/StarRating";

interface LogResultItemProps {
  item: LogSearchResult;
}

export function LogResultItem({ item }: LogResultItemProps) {
  const [searchParams] = useSearchParams();
  const query = searchParams.get("q") || "";
  const navigate = useNavigate();
  const { getConditionInfo } = useConditionInfo();

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
      className="hover:shadow-lg dark:hover:shadow-gray-900/70 transition-shadow cursor-pointer"
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
                  <span className="text-gray-400 dark:text-gray-500 mx-2">·</span>
                  <span className="font-normal text-gray-700 dark:text-gray-300">
                    {item.trig_name}
                  </span>
                </>
              )}
            </Link>
            <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
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
              <span className="text-gray-400 dark:text-gray-500">·</span>
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
              <span className="text-gray-400 dark:text-gray-500">·</span>
              <span className="text-gray-700 dark:text-gray-300">{formattedDate}</span>
              {item.time && item.time !== "12:00:00" && (
                <span className="text-gray-500 dark:text-gray-400 text-xs">{item.time}</span>
              )}
            </div>
          </div>
        </div>

        {/* Comment with highlighting */}
        {item.comment && (
          <div className="flex-[2] min-w-0">
            <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">
              {highlightText(item.comment, query)}
            </p>
          </div>
        )}
      </div>
    </Card>
  );
}
