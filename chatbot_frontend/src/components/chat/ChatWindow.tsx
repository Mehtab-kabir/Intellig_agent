import React, { useState, useRef, useEffect } from "react";
import {
  Bot,
  User,
  Copy,
  Check,
  Send,
  Loader2,
  Menu,
  MessageSquare,
} from "lucide-react";
import { Message } from "../../api/chat";
import { useChatStore } from "../../stores/chatStore";

// Message Bubble
const MessageBubble: React.FC<{ message: Message }> = ({ message }) => {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={`flex gap-4 message-enter ${isUser ? "flex-row-reverse" : ""}`}
    >
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
          isUser ? "bg-primary-600 text-white" : "bg-slate-700 text-slate-300"
        }`}
      >
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>
      <div className={`flex-1 max-w-3xl ${isUser ? "text-right" : ""}`}>
        <div
          className={`inline-block px-4 py-3 rounded-2xl ${
            isUser
              ? "bg-primary-600 text-white rounded-tr-md"
              : "bg-slate-800 text-slate-100 rounded-tl-md"
          }`}
        >
          <p className="whitespace-pre-wrap text-sm leading-relaxed">
            {message.content}
          </p>
        </div>
        <div
          className={`flex items-center gap-2 mt-1 ${
            isUser ? "justify-end" : ""
          }`}
        >
          {!isUser && (
            <button
              onClick={handleCopy}
              className="p-1 text-slate-500 hover:text-slate-300"
              title="Copy"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-green-500" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </button>
          )}
          <span className="text-xs text-slate-500">
            {new Date(message.created_at).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
      </div>
    </div>
  );
};

// Typing Indicator
const TypingIndicator: React.FC = () => (
  <div className="flex gap-4 message-enter">
    <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-slate-700 text-slate-300 flex items-center justify-center">
      <Bot className="w-4 h-4" />
    </div>
    <div className="flex items-center gap-1 px-4 py-3 bg-slate-800 rounded-2xl rounded-tl-md">
      <div className="typing-dot"></div>
      <div className="typing-dot"></div>
      <div className="typing-dot"></div>
    </div>
  </div>
);

// Message Input
const MessageInput: React.FC<{
  onSend: (msg: string) => void;
  isLoading: boolean;
}> = ({ onSend, isLoading }) => {
  const [message, setMessage] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        200
      )}px`;
    }
  }, [message]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isLoading) {
      onSend(message.trim());
      setMessage("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="p-4 border-t border-slate-800 bg-slate-900/50"
    >
      <div className="max-w-4xl mx-auto">
        <div className="relative flex items-end gap-2 bg-slate-800 rounded-2xl p-2">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Send a message..."
            disabled={isLoading}
            rows={1}
            className="flex-1 resize-none bg-transparent text-white placeholder-slate-500 px-4 py-2 focus:outline-none max-h-48 text-sm"
          />
          <button
            type="submit"
            disabled={!message.trim() || isLoading}
            className="flex-shrink-0 p-2.5 bg-primary-600 hover:bg-primary-700 disabled:bg-slate-700 text-white rounded-xl transition-colors"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
        <p className="text-xs text-slate-500 text-center mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </form>
  );
};

// Chat Window
export const ChatWindow: React.FC<{ onMenuClick: () => void }> = ({
  onMenuClick,
}) => {
  const { messages, isSending, sendMessage, error, clearError } =
    useChatStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  return (
    <div className="flex-1 flex flex-col h-screen bg-slate-900">
      <header className="flex items-center gap-4 px-4 py-3 border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm">
        <button
          onClick={onMenuClick}
          className="lg:hidden p-2 text-slate-400 hover:text-white"
        >
          <Menu className="w-5 h-5" />
        </button>
        <h1 className="text-lg font-semibold text-white">Chat</h1>
      </header>

      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center px-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center mb-4">
              <MessageSquare className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-xl font-semibold text-white mb-2">
              How can I help you today?
            </h2>
            <p className="text-slate-400 max-w-md">
              Start a conversation by typing a message below.
            </p>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
            {isSending && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {error && (
        <div className="px-4 py-2 bg-red-500/10 border-t border-red-500/30">
          <div className="max-w-4xl mx-auto flex items-center justify-between">
            <p className="text-sm text-red-400">{error}</p>
            <button
              onClick={clearError}
              className="text-sm text-red-400 hover:text-red-300"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      <MessageInput onSend={sendMessage} isLoading={isSending} />
    </div>
  );
};
