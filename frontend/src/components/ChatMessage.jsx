import ReactMarkdown from 'react-markdown';
import JobCard from './JobCard';

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user';

  const renderJobs = () => {
    if (message.message_type !== 'jobs' || !message.extra_data?.jobs) return null;

    const jobs = message.extra_data.jobs;
    return (
      <div className="grid gap-3 mt-4">
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
            index={idx}
          />
        ))}
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
      </div>
    </div>
  );
}
