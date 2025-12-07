import { create } from "zustand";
import { chatApi, Message, Conversation, ChatResponse } from "../api/chat";

interface ChatState {
  conversations: Conversation[];
  activeConversationId: string | null;
  messages: Message[];
  isLoading: boolean;
  isSending: boolean;
  error: string | null;
  loadConversations: () => Promise<void>;
  selectConversation: (id: string | null) => Promise<void>;
  sendMessage: (prompt: string) => Promise<ChatResponse>;
  startNewChat: () => void;
  deleteConversation: (id: string) => Promise<void>;
  clearError: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  activeConversationId: null,
  messages: [],
  isLoading: false,
  isSending: false,
  error: null,

  loadConversations: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await chatApi.getConversations();
      set({ conversations: response.results, isLoading: false });
    } catch {
      set({ error: "Failed to load conversations", isLoading: false });
    }
  },

  selectConversation: async (id) => {
    if (!id) {
      set({ activeConversationId: null, messages: [] });
      return;
    }
    set({ activeConversationId: id, isLoading: true, error: null });
    try {
      const messages = await chatApi.getMessages(id);
      set({ messages, isLoading: false });
    } catch {
      set({ error: "Failed to load messages", isLoading: false });
    }
  },

  sendMessage: async (prompt) => {
    const { activeConversationId, messages } = get();

    const tempUserMessage: Message = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: prompt,
      created_at: new Date().toISOString(),
      sequence_number: messages.length + 1,
    };

    set({
      messages: [...messages, tempUserMessage],
      isSending: true,
      error: null,
    });

    try {
      const response = await chatApi.sendMessage({
        prompt,
        conversation_id: activeConversationId || undefined,
      });

      const aiMessage: Message = {
        id: response.message_id,
        role: "assistant",
        content: response.response,
        created_at: new Date().toISOString(),
        sequence_number: messages.length + 2,
        response_time_ms: response.response_time_ms,
      };

      set((state) => ({
        messages: [
          ...state.messages.filter((m) => m.id !== tempUserMessage.id),
          { ...tempUserMessage, id: `user-${Date.now()}` },
          aiMessage,
        ],
        activeConversationId: response.conversation_id,
        isSending: false,
      }));

      get().loadConversations();
      return response;
    } catch (error: any) {
      set((state) => ({
        messages: state.messages.filter((m) => m.id !== tempUserMessage.id),
        isSending: false,
        error: error.response?.data?.error?.message || "Failed to send message",
      }));
      throw error;
    }
  },

  startNewChat: () =>
    set({ activeConversationId: null, messages: [], error: null }),

  deleteConversation: async (id) => {
    try {
      await chatApi.deleteConversation(id);
      set((state) => ({
        conversations: state.conversations.filter((c) => c.id !== id),
        ...(state.activeConversationId === id
          ? { activeConversationId: null, messages: [] }
          : {}),
      }));
    } catch {
      set({ error: "Failed to delete conversation" });
    }
  },

  clearError: () => set({ error: null }),
}));
