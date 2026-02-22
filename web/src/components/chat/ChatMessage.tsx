import { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage as ChatMessageType } from "../../hooks/useChat";

const TOOL_LABELS: Record<string, string> = {
  vector_search: "Searching the Retriangulation book",
  query_database: "Querying the database",
};

function ToolIndicator({
  tool,
}: {
  tool: string;
  input: Record<string, unknown>;
}) {
  const label = TOOL_LABELS[tool] || tool;
  return (
    <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)] py-1">
      <svg
        className="h-3.5 w-3.5 animate-spin"
        viewBox="0 0 24 24"
        fill="none"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        />
      </svg>
      <span>{label}…</span>
    </div>
  );
}

function ChatMessage({ message }: { message: ChatMessageType }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "bg-trig-green-600 text-white"
            : "bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)]"
        }`}
      >
        {/* Tool call indicators */}
        {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mb-2 space-y-1 border-b border-[var(--color-border)] pb-2">
            {message.toolCalls.map((tc, i) => (
              <ToolIndicator key={i} tool={tc.tool} input={tc.input} />
            ))}
          </div>
        )}

        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : message.content ? (
          <div className="prose prose-sm dark:prose-invert max-w-none [&_p]:my-1.5 [&_ul]:my-1.5 [&_ol]:my-1.5 [&_li]:my-0.5 [&_pre]:bg-[var(--color-bg-secondary)] [&_pre]:rounded-lg [&_code]:text-xs [&_table]:text-xs">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        ) : message.isStreaming ? (
          <div className="flex gap-1 py-1">
            <span className="h-2 w-2 rounded-full bg-[var(--color-text-muted)] animate-bounce [animation-delay:0ms]" />
            <span className="h-2 w-2 rounded-full bg-[var(--color-text-muted)] animate-bounce [animation-delay:150ms]" />
            <span className="h-2 w-2 rounded-full bg-[var(--color-text-muted)] animate-bounce [animation-delay:300ms]" />
          </div>
        ) : null}

        {/* Streaming cursor */}
        {!isUser && message.isStreaming && message.content && (
          <span className="inline-block h-4 w-0.5 bg-[var(--color-text-muted)] animate-pulse ml-0.5 align-text-bottom" />
        )}
      </div>
    </div>
  );
}

export default memo(ChatMessage);
