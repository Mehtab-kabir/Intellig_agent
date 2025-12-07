import api from "./axios";

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  token_count?: number;
  response_time_ms?: number;
  sequence_number: number;
}

export interface Conversation {
  id: string;
  title: string;
  status: string;
  created_at: string;
  last_message_at: string;
  message_count: number;
  preview?: string;
}

export interface ChatResponse {
  response: string;
  conversation_id: string;
  message_id: string;
  tokens_used: number;
  response_time_ms: number;
  model: string;
}

export interface SendMessageParams {
  prompt: string;
  conversation_id?: string;
  system_prompt?: string;
}

export const chatApi = {
  sendMessage: async (params: SendMessageParams): Promise<ChatResponse> => {
    const response = await api.post("/chat/message/", params);
    return response.data;
  },

  getConversations: async (): Promise<{ results: Conversation[] }> => {
    const response = await api.get("/conversations/");
    return response.data;
  },

  getMessages: async (conversationId: string): Promise<Message[]> => {
    const response = await api.get(
      `/conversations/${conversationId}/messages/`
    );
    return response.data;
  },

  deleteConversation: async (id: string): Promise<void> => {
    await api.delete(`/conversations/${id}/`);
  },
};
