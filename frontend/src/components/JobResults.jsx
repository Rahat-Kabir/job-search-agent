import JobCard from './JobCard';

export default function JobResults({ results, status, isLoading }) {
  if (isLoading) {
    return (
      <section className="card p-10">
        <h2 className="section-title mb-6">Search Results</h2>
        <div className="flex flex-col items-center py-12">
          <div className="w-10 h-10 border-2 border-[rgb(var(--accent))] border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-[rgb(var(--muted-foreground))]">
            {status === 'running' ? 'Searching job boards...' : 'Starting search...'}
          </p>
          <p className="text-sm text-[rgb(var(--muted-foreground))] mt-2">
            This may take a moment
          </p>
        </div>
      </section>
    );
  }

  if (!results || results.length === 0) {
    return null;
  }

  return (
    <section className="card p-10">
      <div className="flex items-center justify-between mb-6">
        <h2 className="section-title">Search Results</h2>
        <span className="text-sm text-[rgb(var(--muted-foreground))]">
          {results.length} job{results.length !== 1 ? 's' : ''} found
        </span>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {results.map((job) => (
          <JobCard key={job.id} job={job} />
        ))}
      </div>
    </section>
  );
}
