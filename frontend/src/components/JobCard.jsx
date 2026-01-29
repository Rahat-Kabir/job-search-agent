export default function JobCard({ job }) {
  const scoreColor = job.match_score >= 0.8
    ? 'text-green-600 dark:text-green-400'
    : job.match_score >= 0.6
      ? 'text-yellow-600 dark:text-yellow-400'
      : 'text-[rgb(var(--muted-foreground))]';

  return (
    <div className="card p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold truncate">{job.title}</h3>
          <p className="text-[rgb(var(--muted-foreground))]">{job.company}</p>
        </div>
        <div className={`text-right ${scoreColor}`}>
          <p className="text-2xl font-bold">{Math.round(job.match_score * 100)}%</p>
          <p className="text-xs">match</p>
        </div>
      </div>

      {job.match_reason && (
        <p className="text-sm text-[rgb(var(--muted-foreground))] mb-4 line-clamp-2">
          {job.match_reason}
        </p>
      )}

      <div className="flex items-center gap-3 mb-4">
        {job.location_type && job.location_type !== 'unknown' && (
          <span className="px-2.5 py-1 text-xs rounded-md bg-[rgb(var(--muted))] capitalize">
            {job.location_type}
          </span>
        )}
        {job.salary && (
          <span className="px-2.5 py-1 text-xs rounded-md bg-[rgb(var(--muted))]">
            {job.salary}
          </span>
        )}
      </div>

      {job.posting_url && (
        <a
          href={job.posting_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 text-sm text-[rgb(var(--accent))] hover:underline"
        >
          View Job
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
      )}
    </div>
  );
}
