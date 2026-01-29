import { useState, useRef } from 'react';

export default function CVUpload({ onUpload, isLoading }) {
  const [dragActive, setDragActive] = useState(false);
  const [fileName, setFileName] = useState(null);
  const inputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = (file) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('Please upload a PDF file');
      return;
    }
    setFileName(file.name);
    onUpload(file);
  };

  return (
    <section className="card p-10">
      <h2 className="section-title mb-6">Upload Your CV</h2>

      <div
        className={`
          relative border-2 border-dashed rounded-2xl p-12
          flex flex-col items-center justify-center
          transition-all duration-200 cursor-pointer
          ${dragActive
            ? 'border-[rgb(var(--accent))] bg-[rgb(var(--accent))]/5'
            : 'border-[rgb(var(--border))] hover:border-[rgb(var(--muted-foreground))]'
          }
          ${isLoading ? 'opacity-50 pointer-events-none' : ''}
        `}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          onChange={handleChange}
          className="hidden"
        />

        {isLoading ? (
          <div className="flex flex-col items-center gap-4">
            <div className="w-8 h-8 border-2 border-[rgb(var(--accent))] border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-[rgb(var(--muted-foreground))]">Analyzing your CV...</p>
          </div>
        ) : (
          <>
            <div className="w-16 h-16 mb-4 rounded-2xl bg-[rgb(var(--muted))] flex items-center justify-center">
              <svg className="w-8 h-8 text-[rgb(var(--muted-foreground))]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <p className="text-base font-medium mb-1">
              {fileName || 'Drop your CV here'}
            </p>
            <p className="text-sm text-[rgb(var(--muted-foreground))]">
              or click to browse (PDF only)
            </p>
          </>
        )}
      </div>
    </section>
  );
}
