export default function SearchButton({ onSearch, isLoading, disabled }) {
  return (
    <section className="card p-10">
      <h2 className="section-title mb-6">Find Jobs</h2>

      <div className="flex flex-col items-center py-4">
        <p className="text-[rgb(var(--muted-foreground))] mb-6 text-center max-w-md">
          Our AI will search multiple job boards and match opportunities to your profile.
        </p>

        <button
          onClick={onSearch}
          disabled={disabled || isLoading}
          className="btn-primary flex items-center gap-3 px-8 py-4 text-lg"
        >
          {isLoading ? (
            <>
              <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
              Searching...
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              Start Search
            </>
          )}
        </button>
      </div>
    </section>
  );
}
