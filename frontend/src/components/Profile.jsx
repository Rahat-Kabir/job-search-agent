import { useState } from 'react';

export default function Profile({ profile, preferences, onUpdatePreferences, isLoading }) {
  const [editing, setEditing] = useState(false);
  const [localPrefs, setLocalPrefs] = useState(preferences);

  const handleSave = () => {
    onUpdatePreferences(localPrefs);
    setEditing(false);
  };

  if (!profile) return null;

  return (
    <section className="card p-10">
      <div className="flex items-center justify-between mb-6">
        <h2 className="section-title">Your Profile</h2>
        {!editing && (
          <button
            onClick={() => setEditing(true)}
            className="text-sm text-[rgb(var(--accent))] hover:underline"
          >
            Edit preferences
          </button>
        )}
      </div>

      <div className="space-y-6">
        {/* Summary */}
        {profile.summary && (
          <div>
            <p className="text-sm text-[rgb(var(--muted-foreground))] mb-2">Summary</p>
            <p className="text-base">{profile.summary}</p>
          </div>
        )}

        {/* Skills */}
        {profile.skills?.length > 0 && (
          <div>
            <p className="text-sm text-[rgb(var(--muted-foreground))] mb-3">Skills</p>
            <div className="flex flex-wrap gap-2">
              {profile.skills.map((skill, i) => (
                <span
                  key={i}
                  className="px-3 py-1.5 text-sm rounded-lg bg-[rgb(var(--muted))]"
                >
                  {skill.name}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Experience & Titles */}
        <div className="grid grid-cols-2 gap-6">
          {profile.experience_years && (
            <div>
              <p className="text-sm text-[rgb(var(--muted-foreground))] mb-1">Experience</p>
              <p className="text-lg font-medium">{profile.experience_years} years</p>
            </div>
          )}
          {profile.job_titles?.length > 0 && (
            <div>
              <p className="text-sm text-[rgb(var(--muted-foreground))] mb-1">Recent Roles</p>
              <p className="text-base">{profile.job_titles.join(', ')}</p>
            </div>
          )}
        </div>

        {/* Preferences Section */}
        <div className="pt-6 border-t border-[rgb(var(--border))]">
          <p className="text-sm text-[rgb(var(--muted-foreground))] mb-4">Job Preferences</p>

          {editing ? (
            <div className="space-y-4">
              <div>
                <label className="text-sm mb-2 block">Location Type</label>
                <select
                  value={localPrefs.location_type}
                  onChange={(e) => setLocalPrefs({ ...localPrefs, location_type: e.target.value })}
                  className="input"
                >
                  <option value="any">Any</option>
                  <option value="remote">Remote</option>
                  <option value="hybrid">Hybrid</option>
                  <option value="onsite">Onsite</option>
                </select>
              </div>

              <div>
                <label className="text-sm mb-2 block">Target Roles (comma-separated)</label>
                <input
                  type="text"
                  value={localPrefs.target_roles?.join(', ') || ''}
                  onChange={(e) => setLocalPrefs({
                    ...localPrefs,
                    target_roles: e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                  })}
                  className="input"
                  placeholder="e.g., Software Engineer, Developer"
                />
              </div>

              <div>
                <label className="text-sm mb-2 block">Minimum Salary</label>
                <input
                  type="number"
                  value={localPrefs.min_salary || ''}
                  onChange={(e) => setLocalPrefs({
                    ...localPrefs,
                    min_salary: e.target.value ? parseInt(e.target.value) : null
                  })}
                  className="input"
                  placeholder="e.g., 100000"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button onClick={handleSave} disabled={isLoading} className="btn-primary">
                  {isLoading ? 'Saving...' : 'Save'}
                </button>
                <button
                  onClick={() => {
                    setLocalPrefs(preferences);
                    setEditing(false);
                  }}
                  className="px-4 py-2 text-sm hover:underline"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-4">
              <div className="p-4 rounded-xl bg-[rgb(var(--muted))]">
                <p className="text-xs text-[rgb(var(--muted-foreground))] mb-1">Location</p>
                <p className="font-medium capitalize">{preferences.location_type || 'Any'}</p>
              </div>
              <div className="p-4 rounded-xl bg-[rgb(var(--muted))]">
                <p className="text-xs text-[rgb(var(--muted-foreground))] mb-1">Target Roles</p>
                <p className="font-medium">{preferences.target_roles?.join(', ') || 'Not set'}</p>
              </div>
              <div className="p-4 rounded-xl bg-[rgb(var(--muted))]">
                <p className="text-xs text-[rgb(var(--muted-foreground))] mb-1">Min Salary</p>
                <p className="font-medium">
                  {preferences.min_salary ? `$${preferences.min_salary.toLocaleString()}` : 'Not set'}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
