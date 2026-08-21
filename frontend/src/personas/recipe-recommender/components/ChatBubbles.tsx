import type { ChatMessage } from "../../../types/persona";

interface ChatBubblesProps {
  /** Most recent user message and AI reply -- the wireframe only shows
   * the latest exchange as sticky notes, not a full scrollback. Full
   * history still lives in ChatRequest.history for the API call; this
   * is just what's visually pinned to the board at once. */
  lastUserMessage: ChatMessage | null;
  lastAiMessage: ChatMessage | null;
}

/**
 * Two stacked sticky notes, top-left of the shell -- user's message
 * above, AI's reply below, per the locked wireframe. Persistent across
 * every tab, not just Chat, matching the reference photos.
 */
export function ChatBubbles({ lastUserMessage, lastAiMessage }: ChatBubblesProps) {
  return (
    <div className="absolute left-6 top-6 flex flex-col gap-3 w-64 z-10">
      {lastUserMessage && (
        <div
          className="rounded-lg px-4 py-3 shadow-md -rotate-1"
          style={{ backgroundColor: "var(--color-bubble-user)" }}
        >
          <p className="font-hand text-lg" style={{ color: "var(--color-tab-favorites)" }}>
            You
          </p>
          <p className="text-sm" style={{ color: "var(--color-parchment)" }}>
            {lastUserMessage.content}
          </p>
        </div>
      )}
      {lastAiMessage && (
        <div
          className="rounded-lg px-4 py-3 shadow-md rotate-1"
          style={{ backgroundColor: "var(--color-bubble-ai)" }}
        >
          <p className="font-hand text-lg" style={{ color: "var(--color-accent)" }}>
            Chef
          </p>
          <p className="text-sm" style={{ color: "var(--color-ink)" }}>
            {lastAiMessage.content}
          </p>
        </div>
      )}
    </div>
  );
}