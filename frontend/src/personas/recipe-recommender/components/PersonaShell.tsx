import type { ReactNode } from "react";
import type { ChatMessage } from "../../../types/persona";
import type { PersonaTab } from "../types";
import { ChefAvatar } from "./ChefAvatar";
import { ChatBubbles } from "./ChatBubbles";
import { ChatInput } from "./ChatInput";
import { SpineTabs } from "./SpineTabs";
import { Book } from "./Book";

interface PersonaShellProps {
  activeTab: PersonaTab;
  onTabChange: (tab: PersonaTab) => void;
  lastUserMessage: ChatMessage | null;
  lastAiMessage: ChatMessage | null;
  onSendMessage: (message: string) => void;
  chatDisabled?: boolean;
  isBookOpen: boolean;
  coverTitle?: string;
  leftPage?: ReactNode;
  rightPage?: ReactNode;
}

/**
 * The persistent frame every tab renders inside -- wood backdrop, chef
 * avatar + chat bubbles pinned top-left, the book (with spine-tab nav)
 * centered, and the chat input always available at the bottom. This is
 * the shared shell described in the Phase Recipe Recommender devlog's
 * Frontend > Context section; individual tabs only ever provide their
 * own leftPage/rightPage content, never their own chrome.
 */
export function PersonaShell({
  activeTab,
  onTabChange,
  lastUserMessage,
  lastAiMessage,
  onSendMessage,
  chatDisabled,
  isBookOpen,
  coverTitle,
  leftPage,
  rightPage,
}: PersonaShellProps) {
  return (
    <div
      className="min-h-screen w-full flex flex-col items-center justify-between p-6 relative"
      style={{ backgroundColor: "var(--color-wood-dark)" }}
    >
      <div className="w-full flex-1 relative flex items-center justify-center">
        <ChatBubbles lastUserMessage={lastUserMessage} lastAiMessage={lastAiMessage} />
        <div className="absolute left-6 bottom-6">
          <ChefAvatar />
        </div>

        <Book
          isOpen={isBookOpen}
          coverTitle={coverTitle}
          leftPage={leftPage}
          rightPage={rightPage}
          spineTabs={<SpineTabs activeTab={activeTab} onChange={onTabChange} />}
        />
      </div>

      <div className="w-full pt-6">
        <ChatInput onSend={onSendMessage} disabled={chatDisabled} />
      </div>
    </div>
  );
}