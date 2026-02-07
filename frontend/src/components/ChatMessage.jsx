import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import JobCard from './JobCard';

export default function ChatMessage({ message, onConfirm, onGetDetails, onUploadCV, onDescribeSkills, bookmarkedUrls = new Set(), onBookmark, onUnbookmark }) {
  const isUser = message.role === 'user';
  const [selectedJobs, setSelectedJobs] = useState(new Set());

  const toggleJob = (idx) => {
    setSelectedJobs(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const handleGetDetails = () => {
    const jobs = message.extra_data?.jobs || [];
    const urls = [...selectedJobs].map(idx => jobs[idx]?.url).filter(Boolean);
    if (urls.length > 0 && onGetDetails) {
      onGetDetails(urls);
    }
  };

  const renderJobs = () => {
    const isSelection = message.message_type === 'job_selection';
    const isJobs = message.message_type === 'jobs';
    if ((!isSelection && !isJobs) || !message.extra_data?.jobs) return null;

    const jobs = message.extra_data.jobs;
    const details = message.extra_data?.details || [];

    // Merge details into jobs by URL
    const enrichedJobs = jobs.map(job => {
      const detail = details.find(d => d.url === job.url);
      return detail ? { ...job, ...detail } : job;
    });

    return (
      <div className="mt-4">
        {isSelection && (
          <div className="flex items-center justify-between mb-3 px-1">
            <span className="text-xs text-[rgb(var(--muted-foreground))]">
              {selectedJobs.size > 0 ? `${selectedJobs.size} selected` : 'Select jobs for detailed info'}
            </span>
            {selectedJobs.size > 0 && onGetDetails && (
              <button
                onClick={handleGetDetails}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg text-white transition-all duration-200 hover:scale-105 active:scale-95"
                style={{ backgroundColor: 'rgb(var(--accent))' }}
              >
                Get Details ({selectedJobs.size})
              </button>
            )}
          </div>
        )}
        <div className="grid gap-3">
          {enrichedJobs.map((job, idx) => {
            const jobUrl = job.url || '';
            const isBookmarked = bookmarkedUrls.has(jobUrl);
            return (
              <JobCard
                key={idx}
                job={{
                  ...job,
                  match_score: (job.score || 0) / 100,
                  match_reason: job.reason || '',
                  location_type: job.location || 'unknown',
                  posting_url: jobUrl,
                }}
                index={idx}
                selectable={isSelection}
                selected={selectedJobs.has(idx)}
                onSelect={() => toggleJob(idx)}
                isBookmarked={isBookmarked}
                onBookmark={onBookmark}
                onUnbookmark={onUnbookmark}
              />
            );
          })}
        </div>
      </div>
    );
  };

  const renderProfile = () => {
    if (message.message_type !== 'profile' || !message.extra_data?.profile) return null;

    const profile = message.extra_data.profile;
    return (
      <div className="mt-4 p-4 rounded-xl border border-[rgb(var(--border))] bg-[rgb(var(--muted))]">
        <h4 className="font-bold text-sm mb-3 flex items-center gap-2">
          <svg className="w-4 h-4 text-[rgb(var(--accent))]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
          Your Profile
        </h4>
        {profile.skills?.length > 0 && (
          <div className="mb-2.5">
            <span className="text-xs font-medium text-[rgb(var(--muted-foreground))] uppercase tracking-wider">Skills</span>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {profile.skills.map((skill, i) => (
                <span key={i} className="px-2 py-0.5 text-xs rounded-md bg-[rgb(var(--accent)/_0.1)] text-[rgb(var(--accent))] font-medium">
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}
        {profile.experience_years && (
          <div className="mb-2">
            <span className="text-xs font-medium text-[rgb(var(--muted-foreground))] uppercase tracking-wider">Experience</span>
            <p className="text-sm mt-0.5">{profile.experience_years} years</p>
          </div>
        )}
        {profile.titles?.length > 0 && (
          <div className="mb-2">
            <span className="text-xs font-medium text-[rgb(var(--muted-foreground))] uppercase tracking-wider">Roles</span>
            <p className="text-sm mt-0.5">{profile.titles.join(' / ')}</p>
          </div>
        )}
        {profile.summary && (
          <div>
            <span className="text-xs font-medium text-[rgb(var(--muted-foreground))] uppercase tracking-wider">Summary</span>
            <p className="text-sm mt-0.5 leading-relaxed">{profile.summary}</p>
          </div>
        )}
      </div>
    );
  };

  const renderOnboarding = () => {
    if (message.message_type !== 'onboarding') return null;

    return (
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          onClick={onUploadCV}
          className="px-4 py-2.5 text-sm font-medium rounded-xl text-white transition-all duration-200 hover:scale-105 active:scale-95 flex items-center gap-2"
          style={{ backgroundColor: 'rgb(var(--accent))' }}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          Yes, upload my CV
        </button>
        <button
          onClick={onDescribeSkills}
          className="px-4 py-2.5 text-sm font-medium rounded-xl border border-[rgb(var(--border))] text-[rgb(var(--foreground))] hover:bg-[rgb(var(--muted))] transition-all duration-200 flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
          No, I'll describe my skills
        </button>
      </div>
    );
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4 message-enter`}>
      <div
        className={`max-w-[85%] ${
          isUser
            ? 'rounded-2xl rounded-br-sm px-4 py-3 text-white'
            : 'bg-[rgb(var(--card))] border border-[rgb(var(--border))] rounded-2xl rounded-bl-sm px-4 py-3'
        }`}
        style={isUser ? {
          backgroundColor: 'rgb(var(--accent))',
        } : undefined}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
        ) : (
          <div className="prose-chat text-sm leading-relaxed">
            <ReactMarkdown
              components={{
                a: ({ href, children }) => (
                  <a href={href} target="_blank" rel="noopener noreferrer" className="text-[rgb(var(--accent))] underline decoration-[rgb(var(--accent)/_0.3)] hover:decoration-[rgb(var(--accent))] transition-colors">
                    {children}
                  </a>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
        {renderProfile()}
        {renderJobs()}
        {renderOnboarding()}

        {/* HITL Confirmation buttons */}
        {message.message_type === 'confirmation' && onConfirm && (
          <div className="mt-4 flex gap-2">
            <button
              onClick={() => onConfirm(true)}
              className="px-4 py-2 text-sm font-medium rounded-lg text-white transition-all duration-200 hover:scale-105 active:scale-95"
              style={{ backgroundColor: 'rgb(var(--accent))' }}
            >
              Approve Search
            </button>
            <button
              onClick={() => onConfirm(false)}
              className="px-4 py-2 text-sm font-medium rounded-lg border border-[rgb(var(--border))] text-[rgb(var(--muted-foreground))] hover:bg-[rgb(var(--muted))] transition-all duration-200"
            >
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
