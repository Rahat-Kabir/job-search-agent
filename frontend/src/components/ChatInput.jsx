import { useState, useRef } from 'react';

export default function ChatInput({ onSend, onUpload, isLoading }) {
  const [message, setMessage] = useState('');
  const fileInputRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!message.trim() || isLoading) return;

    onSend(message.trim());
    setMessage('');
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      onUpload(file);
      e.target.value = '';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-3 p-4 border-t border-[rgb(var(--border))] bg-[rgb(var(--background))]">
      {/* File upload button */}
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        disabled={isLoading}
        className="flex-shrink-0 p-3 rounded-xl bg-[rgb(var(--muted))] hover:bg-[rgb(var(--border))] transition-colors disabled:opacity-50"
        title="Upload CV"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
        </svg>
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        onChange={handleFileChange}
        className="hidden"
      />

      {/* Message input */}
      <div className="flex-1 relative">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message or upload your CV..."
          disabled={isLoading}
          rows={1}
          className="w-full input resize-none max-h-32 pr-12"
          style={{ minHeight: '48px' }}
        />
      </div>

      {/* Send button */}
      <button
        type="submit"
        disabled={!message.trim() || isLoading}
        className="flex-shrink-0 p-3 rounded-xl bg-[rgb(var(--primary))] text-[rgb(var(--primary-foreground))] hover:opacity-90 transition-opacity disabled:opacity-50"
      >
        {isLoading ? (
          <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        ) : (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        )}
      </button>
    </form>
  );
}
