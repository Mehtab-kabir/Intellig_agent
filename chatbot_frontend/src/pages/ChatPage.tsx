import React, { useEffect, useState } from "react";
import { Sidebar } from "../components/sidebar/Sidebar";
import { ChatWindow } from "../components/chat/ChatWindow";
import { useChatStore } from "../stores/chatStore";
import { useAuthStore } from "../stores/authStore";

export const ChatPage: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { loadConversations } = useChatStore();
  const { checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
    loadConversations();
  }, [checkAuth, loadConversations]);

  return (
    <div className="flex h-screen bg-slate-900">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <ChatWindow onMenuClick={() => setSidebarOpen(true)} />
    </div>
  );
};
