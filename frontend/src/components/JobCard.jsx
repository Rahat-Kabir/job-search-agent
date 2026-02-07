import { useState } from 'react';

function ScoreRing({ score }) {
  const radius = 18;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  const getColor = () => {
    if (score >= 80) return { stroke: 'rgb(var(--success))', bg: 'rgb(var(--success) / 0.1)', text: 'text-[rgb(var(--success))]' };
    if (score >= 60) return { stroke: 'rgb(var(--warning))', bg: 'rgb(var(--warning) / 0.1)', text: 'text-[rgb(var(--warning))]' };
    return { stroke: 'rgb(var(--muted-foreground))', bg: 'rgb(var(--muted-foreground) / 0.1)', text: 'text-[rgb(var(--muted-foreground))]' };
  };

  const color = getColor();

  return (
    <div className="relative flex items-center justify-center flex-shrink-0">
      <svg width="48" height="48" className="-rotate-90">
        <circle cx="24" cy="24" r={radius} fill="none" stroke={color.bg} strokeWidth="3" />
        <circle
          cx="24" cy="24" r={radius} fill="none"
          stroke={color.stroke}
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ animation: 'scoreRingFill 0.8s ease-out forwards' }}
        />
      </svg>
      <span className={`absolute text-xs font-bold ${color.text}`}>{score}%</span>
    </div>
  );
}

export default function JobCard({ job, index = 0, selectable = false, selected = false, onSelect, isBookmarked = false, onBookmark, onUnbookmark }) {
  const [bookmarkLoading, setBookmarkLoading] = useState(false);
  const score = Math.round(job.match_score * 100);

  const locationColors = {
    remote: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
    hybrid: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
    onsite: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
    'on-site': 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
  };

  const locationType = job.location_type?.toLowerCase() || '';
  const locationClass = locationColors[locationType] || 'bg-[rgb(var(--muted))] text-[rgb(var(--muted-foreground))]';

  const handleBookmarkClick = async (e) => {
    e.stopPropagation();
    if (bookmarkLoading) return;
    
    setBookmarkLoading(true);
    try {
      if (isBookmarked) {
        await onUnbookmark?.(job);
      } else {
        await onBookmark?.(job);
      }
    } finally {
      setBookmarkLoading(false);
    }
  };

  return (
    <div
      className={`card p-4 hover:shadow-lg transition-all duration-300 hover:-translate-y-0.5 group ${selected ? 'ring-2 ring-[rgb(var(--accent))] bg-[rgb(var(--accent)/_0.05)]' : ''}`}
      style={{ animationDelay: `${index * 80}ms` }}
      onClick={selectable ? () => onSelect?.(!selected) : undefined}
    >
      <div className="flex items-start gap-3">
        {/* Checkbox for selection mode */}
        {selectable && (
          <div className="flex-shrink-0 pt-1">
            <div className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
              selected
                ? 'border-[rgb(var(--accent))] bg-[rgb(var(--accent))]'
                : 'border-[rgb(var(--border))] hover:border-[rgb(var(--accent)/_0.5)]'
            }`}>
              {selected && (
                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
          </div>
        )}

        {/* Score Ring */}
        <ScoreRing score={score} />

        {/* Job Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="text-sm font-bold truncate leading-tight">{job.title}</h3>
              <p className="text-xs text-[rgb(var(--muted-foreground))] mt-0.5 flex items-center gap-1">
                <svg className="w-3 h-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
                {job.company}
              </p>
            </div>

            {/* Bookmark */}
            <button
              onClick={handleBookmarkClick}
              disabled={bookmarkLoading}
              className={`p-1 rounded-md hover:bg-[rgb(var(--muted))] transition-colors flex-shrink-0 ${isBookmarked ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'} ${bookmarkLoading ? 'cursor-wait' : ''}`}
              title={isBookmarked ? 'Remove bookmark' : 'Bookmark job'}
            >
              <svg className={`w-4 h-4 transition-colors ${isBookmarked ? 'fill-[rgb(var(--accent))] text-[rgb(var(--accent))]' : 'text-[rgb(var(--muted-foreground))]'}`} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} fill={isBookmarked ? 'currentColor' : 'none'}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
            </button>
          </div>

          {/* Tags row */}
          <div className="flex flex-wrap items-center gap-1.5 mt-2">
            {locationType && locationType !== 'unknown' && (
              <span className={`px-2 py-0.5 text-[11px] font-medium rounded-md capitalize ${locationClass}`}>
                {job.location_type}
              </span>
            )}
            {job.salary && (
              <span className="px-2 py-0.5 text-[11px] font-medium rounded-md bg-[rgb(var(--accent)/_0.1)] text-[rgb(var(--accent))]">
                {job.salary}
              </span>
            )}
          </div>

          {/* Match reason */}
          {job.match_reason && (
            <p className="text-xs text-[rgb(var(--muted-foreground))] mt-2 line-clamp-2 leading-relaxed">
              {job.match_reason}
            </p>
          )}

          {/* Enriched details (from detail-scraper Phase 2) */}
          {job.description && (
            <p className="text-xs text-[rgb(var(--foreground)/_0.8)] mt-2 leading-relaxed">
              {job.description}
            </p>
          )}
          {job.requirements?.length > 0 && (
            <div className="mt-2">
              <span className="text-[10px] font-semibold text-[rgb(var(--muted-foreground))] uppercase tracking-wider">Requirements</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {job.requirements.map((req, i) => (
                  <span key={i} className="px-1.5 py-0.5 text-[10px] rounded bg-[rgb(var(--muted))] text-[rgb(var(--muted-foreground))]">
                    {req}
                  </span>
                ))}
              </div>
            </div>
          )}
          {job.benefits?.length > 0 && (
            <div className="mt-2">
              <span className="text-[10px] font-semibold text-[rgb(var(--muted-foreground))] uppercase tracking-wider">Benefits</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {job.benefits.map((b, i) => (
                  <span key={i} className="px-1.5 py-0.5 text-[10px] rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                    {b}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Apply button */}
          {job.posting_url && (
            <a
              href={job.posting_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 mt-3 px-3 py-1.5 text-xs font-semibold rounded-lg
                text-white transition-all duration-200
                hover:shadow-md hover:scale-[1.02] active:scale-[0.98]"
              style={{
                backgroundColor: 'rgb(var(--accent))',
              }}
            >
              Apply Now
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
              </svg>
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
