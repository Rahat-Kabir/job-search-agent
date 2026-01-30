import { useState, useEffect } from 'react';

export default function Sidebar({ currentSessionId, onSelectSession, onNewChat, isOpen, onClose }) {
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    loadSessions();
  }, [currentSessionId]);

  const loadSessions = () => {
    const stored = JSON.parse(localStorage.getItem('chatSessions') || '[]');
    setSessions(stored);
  };

  const formatTime = (dateStr) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const handleDelete = (e, sessionId) => {
    e.stopPropagation();
    const updated = sessions.filter(s => s.id !== sessionId);
    localStorage.setItem('chatSessions', JSON.stringify(updated));
    setSessions(updated);
    if (currentSessionId === sessionId) {
      onNewChat();
    }
  };

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:relative z-50 lg:z-auto top-0 left-0 h-full w-72
          bg-[rgb(var(--sidebar))] border-r border-[rgb(var(--border))]
          flex flex-col transition-transform duration-300 ease-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}
      >
        {/* Sidebar Header */}
        <div className="flex-shrink-0 p-4 border-b border-[rgb(var(--border))]">
          <button
            onClick={onNewChat}
            className="w-full btn-primary flex items-center justify-center gap-2 py-3 text-sm"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            New Chat
          </button>
        </div>

        {/* Session List */}
        <nav className="flex-1 overflow-y-auto p-2">
          {sessions.length === 0 ? (
            <div className="px-3 py-8 text-center">
              <div className="w-10 h-10 mx-auto mb-3 rounded-xl bg-[rgb(var(--muted))] flex items-center justify-center">
                <svg className="w-5 h-5 text-[rgb(var(--muted-foreground))]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
              <p className="text-xs text-[rgb(var(--muted-foreground))]">No conversations yet</p>
              <p className="text-xs text-[rgb(var(--muted-foreground))] mt-1">Start a new chat above</p>
            </div>
          ) : (
            <div className="space-y-0.5">
              {sessions.map((session) => {
                const isActive = session.id === currentSessionId;
                return (
                  <button
                    key={session.id}
                    onClick={() => {
                      onSelectSession(session.id);
                      onClose();
                    }}
                    className={`w-full text-left px-3 py-2.5 rounded-lg group transition-all duration-200
                      ${isActive
                        ? 'bg-[rgb(var(--accent)/_0.1)] text-[rgb(var(--accent))]'
                        : 'hover:bg-[rgb(var(--sidebar-hover))] text-[rgb(var(--foreground))]'
                      }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm font-medium truncate ${isActive ? 'text-[rgb(var(--accent))]' : ''}`}>
                          {session.title || 'New conversation'}
                        </p>
                        {session.preview && (
                          <p className="text-xs text-[rgb(var(--muted-foreground))] truncate mt-0.5">
                            {session.preview}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <span className="text-[10px] text-[rgb(var(--muted-foreground))]">
                          {formatTime(session.updatedAt || session.createdAt)}
                        </span>
                        <button
                          onClick={(e) => handleDelete(e, session.id)}
                          className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-[rgb(var(--muted))] transition-opacity"
                          title="Delete"
                        >
                          <svg className="w-3.5 h-3.5 text-[rgb(var(--muted-foreground))]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </nav>

        {/* Sidebar Footer */}
        <div className="flex-shrink-0 p-3 border-t border-[rgb(var(--border))]">
          <div className="flex items-center gap-2 px-2">
            <div className="w-2 h-2 rounded-full bg-[rgb(var(--success))]" />
            <span className="text-xs text-[rgb(var(--muted-foreground))]">AI Agent Ready</span>
          </div>
        </div>
      </aside>
    </>
  );
}
