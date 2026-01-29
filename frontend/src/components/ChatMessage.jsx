import ReactMarkdown from 'react-markdown';
import JobCard from './JobCard';

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user';

  // Render jobs if message contains job data
  const renderJobs = () => {
    if (message.message_type !== 'jobs' || !message.extra_data?.jobs) return null;

    const jobs = message.extra_data.jobs;
    return (
      <div className="grid gap-4 mt-4">
        {jobs.map((job, idx) => (
          <JobCard
            key={idx}
            job={{
              ...job,
              match_score: (job.score || 0) / 100,
              match_reason: job.reason || '',
              location_type: job.location || 'unknown',
              posting_url: job.url || '',
            }}
          />
        ))}
      </div>
    );
  };

  // Render profile summary if message contains profile data
  const renderProfile = () => {
    if (message.message_type !== 'profile' || !message.extra_data?.profile) return null;

    const profile = message.extra_data.profile;
    return (
      <div className="mt-4 p-4 rounded-xl bg-[rgb(var(--muted))]">
        <h4 className="font-semibold mb-2">Your Profile</h4>
        {profile.skills?.length > 0 && (
          <div className="mb-2">
            <span className="text-sm text-[rgb(var(--muted-foreground))]">Skills: </span>
            <span className="text-sm">{profile.skills.join(', ')}</span>
          </div>
        )}
        {profile.experience_years && (
          <div className="mb-2">
            <span className="text-sm text-[rgb(var(--muted-foreground))]">Experience: </span>
            <span className="text-sm">{profile.experience_years} years</span>
          </div>
        )}
        {profile.titles?.length > 0 && (
          <div className="mb-2">
            <span className="text-sm text-[rgb(var(--muted-foreground))]">Roles: </span>
            <span className="text-sm">{profile.titles.join(', ')}</span>
          </div>
        )}
        {profile.summary && (
          <div>
            <span className="text-sm text-[rgb(var(--muted-foreground))]">Summary: </span>
            <span className="text-sm">{profile.summary}</span>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[85%] ${
          isUser
            ? 'bg-[rgb(var(--primary))] text-[rgb(var(--primary-foreground))] rounded-2xl rounded-br-md px-4 py-3'
            : 'bg-[rgb(var(--card))] border border-[rgb(var(--border))] rounded-2xl rounded-bl-md px-4 py-3'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
        ) : (
          <div className="prose-chat text-sm leading-relaxed">
            <ReactMarkdown
              components={{
                a: ({ href, children }) => (
                  <a href={href} target="_blank" rel="noopener noreferrer" className="text-[rgb(var(--accent))] underline hover:opacity-80">
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
      </div>
    </div>
  );
}
