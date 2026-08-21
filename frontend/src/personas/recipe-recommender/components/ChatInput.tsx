import { useState } from "react";
import type { FormEvent } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

/**
 * Persistent input bar, always visible at the bottom of the shell
 * regardless of active tab -- per the locked design, the chef is always
 * reachable, not just from the Chat tab. Wiring to a real /chat call
 * happens in the next step (useChat hook); this just handles local
 * input state and hands the message up on submit.
 */
export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full max-w-3xl mx-auto flex items-center gap-3 rounded-full px-5 py-3 shadow-lg"
      style={{ backgroundColor: "var(--color-parchment)" }}
    >
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Ask Chef anything..."
        disabled={disabled}
        className="flex-1 bg-transparent outline-none font-body text-base placeholder:italic"
        style={{ color: "var(--color-ink)" }}
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="rounded-full w-9 h-9 flex items-center justify-center shrink-0 disabled:opacity-40"
        style={{ backgroundColor: "var(--color-accent)" }}
        aria-label="Send message"
      >
        <span style={{ color: "var(--color-parchment)" }}>➤</span>
      </button>
    </form>
  );
}
