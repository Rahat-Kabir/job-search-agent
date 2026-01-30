import { useState, useRef } from 'react';

export default function ChatInput({ onSend, onUpload, isLoading }) {
  const [message, setMessage] = useState('');
  const [dragOver, setDragOver] = useState(false);
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

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file && file.type === 'application/pdf') {
      onUpload(file);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      className={`flex items-end gap-2.5 p-3 lg:p-4 border-t transition-colors duration-200
        ${dragOver
          ? 'border-[rgb(var(--accent))] bg-[rgb(var(--accent)/_0.05)]'
          : 'border-[rgb(var(--border))] bg-[rgb(var(--background)/_0.8)]'
        } backdrop-blur-lg`}
    >
      {/* File upload button */}
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        disabled={isLoading}
        className="flex-shrink-0 p-2.5 rounded-xl bg-[rgb(var(--muted))] hover:bg-[rgb(var(--border))]
          transition-all duration-200 disabled:opacity-40 hover:scale-105 active:scale-95
          group"
        title="Upload CV (PDF)"
      >
        <svg className="w-5 h-5 text-[rgb(var(--muted-foreground))] group-hover:text-[rgb(var(--accent))] transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" />
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
          placeholder={dragOver ? 'Drop your CV here...' : 'Ask about jobs, upload your CV...'}
          disabled={isLoading}
          rows={1}
          className="w-full input resize-none max-h-32 pr-4 text-sm"
          style={{ minHeight: '44px' }}
        />
      </div>

      {/* Send button */}
      <button
        type="submit"
        disabled={!message.trim() || isLoading}
        className="flex-shrink-0 p-2.5 rounded-xl transition-all duration-200
          disabled:opacity-30 disabled:cursor-not-allowed
          hover:scale-105 active:scale-95"
        style={{
          backgroundColor: message.trim() && !isLoading
            ? 'rgb(var(--accent))'
            : 'rgb(var(--muted))',
        }}
      >
        {isLoading ? (
          <svg className="w-5 h-5 animate-spin text-[rgb(var(--muted-foreground))]" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        ) : (
          <svg className={`w-5 h-5 ${message.trim() ? 'text-white' : 'text-[rgb(var(--muted-foreground))]'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
          </svg>
        )}
      </button>
    </form>
  );
}
