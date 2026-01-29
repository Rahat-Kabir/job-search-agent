const API_BASE = '/api';

export async function uploadCV(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/cv/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to upload CV');
  }

  return res.json();
}

export async function getProfile(userId) {
  const res = await fetch(`${API_BASE}/profile`, {
    headers: { 'X-User-ID': userId },
  });

  if (!res.ok) {
    throw new Error('Failed to fetch profile');
  }

  return res.json();
}

export async function getPreferences(userId) {
  const res = await fetch(`${API_BASE}/preferences`, {
    headers: { 'X-User-ID': userId },
  });

  if (!res.ok) {
    throw new Error('Failed to fetch preferences');
  }

  return res.json();
}

export async function updatePreferences(userId, preferences) {
  const res = await fetch(`${API_BASE}/preferences`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': userId,
    },
    body: JSON.stringify(preferences),
  });

  if (!res.ok) {
    throw new Error('Failed to update preferences');
  }

  return res.json();
}

export async function startSearch(userId) {
  const res = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': userId,
    },
    body: JSON.stringify({}),
  });

  if (!res.ok) {
    throw new Error('Failed to start search');
  }

  return res.json();
}

export async function getSearchResults(userId, searchId) {
  const res = await fetch(`${API_BASE}/search/results?search_id=${searchId}`, {
    headers: { 'X-User-ID': userId },
  });

  if (!res.ok) {
    throw new Error('Failed to fetch results');
  }

  return res.json();
}

// Chat API
export async function sendMessage(message, sessionId = null) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to send message');
  }

  return res.json();
}

export async function uploadCVChat(file, sessionId = null) {
  const formData = new FormData();
  formData.append('file', file);
  if (sessionId) {
    formData.append('session_id', sessionId);
  }

  const res = await fetch(`${API_BASE}/chat/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to upload CV');
  }

  return res.json();
}

export async function getChatHistory(sessionId) {
  const res = await fetch(`${API_BASE}/chat/${sessionId}`);

  if (!res.ok) {
    throw new Error('Failed to fetch chat history');
  }

  return res.json();
}
