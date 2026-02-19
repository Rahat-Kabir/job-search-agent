const API_BASE = '/api';

async function readErrorMessage(res, fallbackMessage) {
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try {
      const error = await res.json();
      return error.detail || error.message || fallbackMessage;
    } catch {
      return fallbackMessage;
    }
  }

  try {
    const text = (await res.text()).trim();
    if (!text) return fallbackMessage;
    return text.slice(0, 300);
  } catch {
    return fallbackMessage;
  }
}

export async function uploadCV(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/cv/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const msg = await readErrorMessage(res, 'Failed to upload CV');
    throw new Error(msg);
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

// Helper to build headers with optional auth
function _authHeaders(userId, contentType = null) {
  const headers = {};
  if (contentType) headers['Content-Type'] = contentType;
  if (userId) headers['X-User-ID'] = userId;
  return headers;
}

// Chat API
export async function sendMessage(message, sessionId = null, userId = null) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: _authHeaders(userId, 'application/json'),
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to send message');
  }

  return res.json();
}

export async function uploadCVChat(file, sessionId = null, userId = null) {
  const formData = new FormData();
  formData.append('file', file);
  if (sessionId) {
    formData.append('session_id', sessionId);
  }

  const res = await fetch(`${API_BASE}/chat/upload`, {
    method: 'POST',
    headers: _authHeaders(userId),
    body: formData,
  });

  if (!res.ok) {
    const msg = await readErrorMessage(res, 'Failed to upload CV');
    throw new Error(msg);
  }

  return res.json();
}

export async function getChatHistory(sessionId, userId = null) {
  const res = await fetch(`${API_BASE}/chat/${sessionId}`, {
    headers: _authHeaders(userId),
  });

  if (!res.ok) {
    throw new Error('Failed to fetch chat history');
  }

  return res.json();
}

export async function listSessions(userId = null) {
  const res = await fetch(`${API_BASE}/chat/sessions`, {
    headers: _authHeaders(userId),
  });

  if (!res.ok) {
    throw new Error('Failed to fetch sessions');
  }

  return res.json();
}

export async function deleteSession(sessionId, userId = null) {
  const res = await fetch(`${API_BASE}/chat/${sessionId}`, {
    method: 'DELETE',
    headers: _authHeaders(userId),
  });

  if (!res.ok) {
    throw new Error('Failed to delete session');
  }

  return res.json();
}

// HITL Confirmation (SSE streaming)
export async function confirmAction(sessionId, approved, onStatus, onComplete, onError, userId = null) {
  try {
    const response = await fetch(`${API_BASE}/chat/confirm`, {
      method: 'POST',
      headers: _authHeaders(userId, 'application/json'),
      body: JSON.stringify({ session_id: sessionId, approved }),
    });

    if (!response.ok) {
      const msg = await readErrorMessage(response, 'Failed to confirm action');
      throw new Error(msg);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const chunk of lines) {
        if (!chunk.trim()) continue;

        const eventMatch = chunk.match(/^event: (\w+)/);
        const dataMatch = chunk.match(/^data: (.+)$/m);

        if (eventMatch && dataMatch) {
          const event = eventMatch[1];
          try {
            const data = JSON.parse(dataMatch[1]);

            if (event === 'status') onStatus?.(data);
            else if (event === 'agent_event') onStatus?.({ stage: data.type, message: data.message });
            else if (event === 'done') onComplete?.(data);
            else if (event === 'error') onError?.(data);
          } catch (parseError) {
            console.error('Failed to parse SSE data:', parseError);
          }
        }
      }
    }
  } catch (err) {
    onError?.({ message: err.message });
    throw err;
  }
}

// Get Job Details (Phase 2 - SSE streaming)
export async function getJobDetails(sessionId, selectedUrls, onStatus, onComplete, onError, userId = null) {
  try {
    const response = await fetch(`${API_BASE}/chat/get-details`, {
      method: 'POST',
      headers: _authHeaders(userId, 'application/json'),
      body: JSON.stringify({ session_id: sessionId, selected_urls: selectedUrls }),
    });

    if (!response.ok) {
      const msg = await readErrorMessage(response, 'Failed to get job details');
      throw new Error(msg);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const chunk of lines) {
        if (!chunk.trim()) continue;

        const eventMatch = chunk.match(/^event: (\w+)/);
        const dataMatch = chunk.match(/^data: (.+)$/m);

        if (eventMatch && dataMatch) {
          const event = eventMatch[1];
          try {
            const data = JSON.parse(dataMatch[1]);

            if (event === 'status') onStatus?.(data);
            else if (event === 'agent_event') onStatus?.({ stage: data.type, message: data.message });
            else if (event === 'done') onComplete?.(data);
            else if (event === 'error') onError?.(data);
          } catch (parseError) {
            console.error('Failed to parse SSE data:', parseError);
          }
        }
      }
    }
  } catch (err) {
    onError?.({ message: err.message });
    throw err;
  }
}

// SSE Streaming Chat API
export async function sendMessageStream(message, sessionId, onStatus, onComplete, onError, onConfirmation, userId = null) {
  try {
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: _authHeaders(userId, 'application/json'),
      body: JSON.stringify({ message, session_id: sessionId }),
    });

    if (!response.ok) {
      const msg = await readErrorMessage(response, 'Failed to send message');
      throw new Error(msg);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const chunk of lines) {
        if (!chunk.trim()) continue;

        const eventMatch = chunk.match(/^event: (\w+)/);
        const dataMatch = chunk.match(/^data: (.+)$/m);

        if (eventMatch && dataMatch) {
          const event = eventMatch[1];
          try {
            const data = JSON.parse(dataMatch[1]);

            if (event === 'status') onStatus?.(data);
            else if (event === 'agent_event') onStatus?.({ stage: data.type, message: data.message });
            else if (event === 'done') onComplete?.(data);
            else if (event === 'confirmation') onConfirmation?.(data);
            else if (event === 'error') onError?.(data);
          } catch (parseError) {
            console.error('Failed to parse SSE data:', parseError);
          }
        }
      }
    }
  } catch (err) {
    onError?.({ message: err.message });
    throw err;
  }
}

// Bookmark API
export async function createBookmark(bookmark, userId = null) {
  const res = await fetch(`${API_BASE}/bookmarks`, {
    method: 'POST',
    headers: _authHeaders(userId, 'application/json'),
    body: JSON.stringify(bookmark),
  });

  if (!res.ok) {
    const msg = await readErrorMessage(res, 'Failed to create bookmark');
    throw new Error(msg);
  }

  return res.json();
}

export async function deleteBookmark(bookmarkId, userId = null) {
  const res = await fetch(`${API_BASE}/bookmarks/${bookmarkId}`, {
    method: 'DELETE',
    headers: _authHeaders(userId),
  });

  if (!res.ok) {
    const msg = await readErrorMessage(res, 'Failed to delete bookmark');
    throw new Error(msg);
  }

  return res.json();
}

export async function deleteBookmarkByUrl(sessionId, postingUrl, userId = null) {
  const res = await fetch(`${API_BASE}/bookmarks/url/${sessionId}?posting_url=${encodeURIComponent(postingUrl)}`, {
    method: 'DELETE',
    headers: _authHeaders(userId),
  });

  if (!res.ok) {
    const msg = await readErrorMessage(res, 'Failed to delete bookmark');
    throw new Error(msg);
  }

  return res.json();
}

export async function listBookmarks(sessionId, userId = null) {
  const res = await fetch(`${API_BASE}/bookmarks?session_id=${sessionId}`, {
    headers: _authHeaders(userId),
  });

  if (!res.ok) {
    throw new Error('Failed to fetch bookmarks');
  }

  return res.json();
}

export async function checkBookmark(sessionId, postingUrl, userId = null) {
  const res = await fetch(`${API_BASE}/bookmarks/check?session_id=${sessionId}&posting_url=${encodeURIComponent(postingUrl)}`, {
    headers: _authHeaders(userId),
  });

  if (!res.ok) {
    throw new Error('Failed to check bookmark');
  }

  return res.json();
}
