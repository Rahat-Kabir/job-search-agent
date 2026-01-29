import { useState, useEffect, useRef } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import * as api from '../api';

const WELCOME_MESSAGE = {
  role: 'assistant',
  content: "Hi! I'm your job search assistant. Upload your CV or tell me about your skills and experience, and I'll help you find the perfect job.",
  message_type: 'text',
  extra_data: {},
  created_at: new Date().toISOString(),
};

export default function Chat() {
  const [sessionId, setSessionId] = useState(() => localStorage.getItem('chatSessionId'));
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);

  // Load chat history on mount
  useEffect(() => {
    if (sessionId) {
      loadHistory();
    }
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadHistory = async () => {
    try {
      const data = await api.getChatHistory(sessionId);
      if (data.messages.length > 0) {
        setMessages(data.messages);
      }
    } catch (err) {
      console.error('Failed to load history:', err);
      // Clear invalid session
      localStorage.removeItem('chatSessionId');
      setSessionId(null);
    }
  };

  const handleSend = async (message) => {
    setError(null);
    setIsLoading(true);

    // Optimistically add user message
    const userMsg = {
      role: 'user',
      content: message,
      message_type: 'text',
      extra_data: {},
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const data = await api.sendMessage(message, sessionId);

      // Save session ID
      if (!sessionId && data.session_id) {
        setSessionId(data.session_id);
        localStorage.setItem('chatSessionId', data.session_id);
      }

      // Update messages with server response
      setMessages(data.messages);
    } catch (err) {
      setError(err.message);
      // Remove optimistic message on error
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpload = async (file) => {
    setError(null);
    setIsLoading(true);

    // Optimistically add upload message
    const userMsg = {
      role: 'user',
      content: `[Uploading: ${file.name}]`,
      message_type: 'text',
      extra_data: {},
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const data = await api.uploadCVChat(file, sessionId);

      // Save session ID
      if (!sessionId && data.session_id) {
        setSessionId(data.session_id);
        localStorage.setItem('chatSessionId', data.session_id);
      }

      // Update messages with server response
      setMessages(data.messages);
    } catch (err) {
      setError(err.message);
      // Remove optimistic message on error
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChat = () => {
    localStorage.removeItem('chatSessionId');
    setSessionId(null);
    setMessages([WELCOME_MESSAGE]);
    setError(null);
  };

  return (
    <div className="flex flex-col h-screen max-h-screen">
      {/* Header */}
      <header className="flex-shrink-0 flex items-center justify-between px-6 py-4 border-b border-[rgb(var(--border))] bg-[rgb(var(--background))]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[rgb(var(--primary))] flex items-center justify-center">
            <svg className="w-6 h-6 text-[rgb(var(--primary-foreground))]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <h1 className="font-semibold">Job Search Agent</h1>
            <p className="text-xs text-[rgb(var(--muted-foreground))]">AI-powered job matching</p>
          </div>
        </div>
        <button
          onClick={handleNewChat}
          className="text-sm px-4 py-2 rounded-lg bg-[rgb(var(--muted))] hover:bg-[rgb(var(--border))] transition-colors"
        >
          New Chat
        </button>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto">
          {error && (
            <div className="mb-4 p-4 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
              {error}
            </div>
          )}

          {messages.map((msg, idx) => (
            <ChatMessage key={idx} message={msg} />
          ))}

          {isLoading && (
            <div className="flex justify-start mb-4">
              <div className="bg-[rgb(var(--card))] border border-[rgb(var(--border))] rounded-2xl rounded-bl-md px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-[rgb(var(--muted-foreground))] animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 rounded-full bg-[rgb(var(--muted-foreground))] animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 rounded-full bg-[rgb(var(--muted-foreground))] animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input */}
      <div className="flex-shrink-0 max-w-3xl mx-auto w-full">
        <ChatInput
          onSend={handleSend}
          onUpload={handleUpload}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}
