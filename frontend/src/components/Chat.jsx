import { useState, useEffect, useRef, useMemo } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import Sidebar from './Sidebar';
import * as api from '../api';

const WELCOME_MESSAGE = {
  role: 'assistant',
  content: "Hey! I'm your AI job search assistant. Let's find you the perfect role.\n\nDo you have a CV/resume ready to upload?",
  message_type: 'onboarding',
  extra_data: {},
  created_at: new Date().toISOString(),
};

export default function Chat() {
  const [sessionId, setSessionId] = useState(() => localStorage.getItem('chatSessionId'));
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [streamingStatus, setStreamingStatus] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [bookmarks, setBookmarks] = useState([]);
  const [dark, setDark] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('theme') === 'dark' ||
        (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches);
    }
    return false;
  });
  const messagesEndRef = useRef(null);
  const onboardingFileRef = useRef(null);

  // Compute set of bookmarked URLs for quick lookup
  const bookmarkedUrls = useMemo(() => {
    return new Set(bookmarks.map(b => b.posting_url));
  }, [bookmarks]);

  // Load bookmarks when session changes
  const loadBookmarks = async (sid) => {
    if (!sid) {
      setBookmarks([]);
      return;
    }
    try {
      const data = await api.listBookmarks(sid);
      setBookmarks(data.bookmarks || []);
    } catch (err) {
      console.error('Failed to load bookmarks:', err);
    }
  };

  // Bookmark handlers
  const handleBookmark = async (job) => {
    if (!sessionId) return;
    try {
      const bookmark = await api.createBookmark({
        session_id: sessionId,
        title: job.title,
        company: job.company,
        match_score: job.match_score,
        match_reason: job.match_reason || job.reason || '',
        location_type: job.location_type || job.location || 'unknown',
        salary: job.salary || null,
        posting_url: job.posting_url || job.url,
        description_snippet: job.description_snippet || '',
      });
      setBookmarks(prev => [bookmark, ...prev]);
    } catch (err) {
      console.error('Failed to bookmark job:', err);
    }
  };

  const handleUnbookmark = async (job) => {
    if (!sessionId) return;
    const url = job.posting_url || job.url;
    try {
      await api.deleteBookmarkByUrl(sessionId, url);
      setBookmarks(prev => prev.filter(b => b.posting_url !== url));
    } catch (err) {
      console.error('Failed to remove bookmark:', err);
    }
  };

  // Dark mode
  useEffect(() => {
    if (dark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [dark]);

  // Load chat history and bookmarks on mount
  useEffect(() => {
    if (sessionId) {
      loadHistory();
      loadBookmarks(sessionId);
    }
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingStatus]);

  const loadHistory = async () => {
    try {
      const data = await api.getChatHistory(sessionId);
      if (data.messages.length > 0) {
        setMessages(data.messages);
      }
    } catch (err) {
      console.error('Failed to load history:', err);
      localStorage.removeItem('chatSessionId');
      setSessionId(null);
    }
  };

  const handleSend = async (message) => {
    setError(null);
    setIsLoading(true);
    setStreamingStatus(null);

    const userMsg = {
      role: 'user',
      content: message,
      message_type: 'text',
      extra_data: {},
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      await api.sendMessageStream(
        message,
        sessionId,
        (status) => {
          setStreamingStatus(status.message);
        },
        (result) => {
          if (!sessionId && result.session_id) {
            setSessionId(result.session_id);
            localStorage.setItem('chatSessionId', result.session_id);
          }
          setMessages((prev) => [...prev, result.message]);
          setIsLoading(false);
          setStreamingStatus(null);
        },
        (error) => {
          setError(error.message);
          setMessages((prev) => prev.slice(0, -1));
          setIsLoading(false);
          setStreamingStatus(null);
        },
        // Handle confirmation (HITL interrupt)
        (result) => {
          if (!sessionId && result.session_id) {
            setSessionId(result.session_id);
            localStorage.setItem('chatSessionId', result.session_id);
          }
          setMessages((prev) => [...prev, result.message]);
          setIsLoading(false);
          setStreamingStatus(null);
        }
      );
    } catch (err) {
      setError(err.message);
      setMessages((prev) => prev.slice(0, -1));
      setIsLoading(false);
      setStreamingStatus(null);
    }
  };

  const handleConfirm = async (approved) => {
    setError(null);
    setIsLoading(true);
    setStreamingStatus(null);

    // Remove confirmation buttons by changing message type
    setMessages((prev) =>
      prev.map((msg, idx) =>
        idx === prev.length - 1 && msg.message_type === 'confirmation'
          ? { ...msg, message_type: 'text', content: approved ? 'Approved! Searching...' : 'Search cancelled.' }
          : msg
      )
    );

    try {
      await api.confirmAction(
        sessionId,
        approved,
        (status) => {
          setStreamingStatus(status.message);
        },
        (result) => {
          setMessages((prev) => [...prev, result.message]);
          setIsLoading(false);
          setStreamingStatus(null);
        },
        (error) => {
          setError(error.message);
          setIsLoading(false);
          setStreamingStatus(null);
        }
      );
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
      setStreamingStatus(null);
    }
  };

  const handleGetDetails = async (selectedUrls) => {
    setError(null);
    setIsLoading(true);
    setStreamingStatus(null);

    try {
      await api.getJobDetails(
        sessionId,
        selectedUrls,
        (status) => {
          setStreamingStatus(status.message);
        },
        (result) => {
          setMessages((prev) => [...prev, result.message]);
          setIsLoading(false);
          setStreamingStatus(null);
        },
        (error) => {
          setError(error.message);
          setIsLoading(false);
          setStreamingStatus(null);
        }
      );
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
      setStreamingStatus(null);
    }
  };

  const handleUpload = async (file) => {
    setError(null);
    setIsLoading(true);

    const userMsg = {
      role: 'user',
      content: `Uploading: ${file.name}`,
      message_type: 'text',
      extra_data: {},
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const data = await api.uploadCVChat(file, sessionId);

      if (!sessionId && data.session_id) {
        setSessionId(data.session_id);
        localStorage.setItem('chatSessionId', data.session_id);
      }

      setMessages(data.messages);
    } catch (err) {
      setError(err.message);
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChat = () => {
    localStorage.removeItem('chatSessionId');
    setSessionId(null);
    setMessages([WELCOME_MESSAGE]);
    setBookmarks([]);
    setError(null);
    setSidebarOpen(false);
  };

  // Onboarding handlers
  const handleOnboardingUpload = () => {
    onboardingFileRef.current?.click();
  };

  const handleOnboardingDescribe = () => {
    // Replace onboarding message with user's choice, then prompt for skills
    setMessages((prev) =>
      prev.map((msg) =>
        msg.message_type === 'onboarding'
          ? { ...msg, message_type: 'text' }
          : msg
      )
    );
    handleSend("I don't have a CV ready. I'd like to describe my skills and experience.");
  };

  const handleOnboardingFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      // Replace onboarding message with text before uploading
      setMessages((prev) =>
        prev.map((msg) =>
          msg.message_type === 'onboarding'
            ? { ...msg, message_type: 'text' }
            : msg
        )
      );
      handleUpload(file);
      e.target.value = '';
    }
  };

  const handleSelectSession = async (sid) => {
    setSessionId(sid);
    localStorage.setItem('chatSessionId', sid);
    setError(null);
    try {
      const data = await api.getChatHistory(sid);
      if (data.messages.length > 0) {
        setMessages(data.messages);
      }
      loadBookmarks(sid);
    } catch (err) {
      console.error('Failed to load session:', err);
      setMessages([WELCOME_MESSAGE]);
      setBookmarks([]);
    }
  };

  return (
    <div className="flex h-screen max-h-screen overflow-hidden relative">
      {/* Sidebar */}
      <Sidebar
        currentSessionId={sessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        bookmarks={bookmarks}
        onRemoveBookmark={handleUnbookmark}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 relative z-10">
        {/* Header */}
        <header className="flex-shrink-0 flex items-center justify-between px-4 lg:px-6 py-3 border-b border-[rgb(var(--border))] bg-[rgb(var(--background)/_0.8)] backdrop-blur-lg">
          <div className="flex items-center gap-3">
            {/* Mobile hamburger */}
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-lg hover:bg-[rgb(var(--muted))] transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            {/* Logo */}
            <div className="w-9 h-9 rounded-xl flex items-center justify-center bg-[rgb(var(--accent))]"
            >
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <h1 className="text-base font-bold tracking-tight accent-text">Job Search Agent</h1>
              <p className="text-[11px] text-[rgb(var(--muted-foreground))] -mt-0.5">AI-powered job matching</p>
            </div>
          </div>

          {/* Theme toggle */}
          <button
            onClick={() => setDark(!dark)}
            className="p-2.5 rounded-xl bg-[rgb(var(--muted))] hover:bg-[rgb(var(--border))] transition-all duration-200 hover:scale-105 active:scale-95"
            aria-label="Toggle dark mode"
          >
            {dark ? (
              <svg className="w-4.5 h-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            ) : (
              <svg className="w-4.5 h-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            )}
          </button>
        </header>

        {/* Messages */}
        <main className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-3xl mx-auto">
            {error && (
              <div className="mb-4 p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-sm message-enter flex items-center gap-2">
                <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {error}
              </div>
            )}

            {messages.map((msg, idx) => (
              <ChatMessage
                key={idx}
                message={msg}
                onConfirm={msg.message_type === 'confirmation' && idx === messages.length - 1 ? handleConfirm : undefined}
                onGetDetails={msg.message_type === 'job_selection' ? handleGetDetails : undefined}
                onUploadCV={msg.message_type === 'onboarding' ? handleOnboardingUpload : undefined}
                onDescribeSkills={msg.message_type === 'onboarding' ? handleOnboardingDescribe : undefined}
                bookmarkedUrls={bookmarkedUrls}
                onBookmark={handleBookmark}
                onUnbookmark={handleUnbookmark}
              />
            ))}

            {/* Hidden file input for onboarding CV upload */}
            <input
              ref={onboardingFileRef}
              type="file"
              accept=".pdf"
              onChange={handleOnboardingFileChange}
              className="hidden"
            />

            {isLoading && (
              <div className="flex justify-start mb-4 message-enter">
                <div className="bg-[rgb(var(--card))] border border-[rgb(var(--border))] rounded-2xl rounded-bl-md px-4 py-3.5">
                  <div className="flex items-center gap-3">
                    <div className="flex gap-1.5">
                      <div className="w-2 h-2 rounded-full typing-dot bg-[rgb(var(--accent))]" />
                      <div className="w-2 h-2 rounded-full typing-dot bg-[rgb(var(--accent)/_0.6)]" />
                      <div className="w-2 h-2 rounded-full typing-dot bg-[rgb(var(--accent)/_0.3)]" />
                    </div>
                    {streamingStatus && (
                      <span className="text-sm text-[rgb(var(--muted-foreground))] italic">
                        {streamingStatus}
                      </span>
                    )}
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
    </div>
  );
}
