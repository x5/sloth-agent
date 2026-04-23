import { useState } from 'react';
import { invoke } from '@tauri-apps/api/core';

function App() {
  const [input, setInput] = useState('');
  const [response, setResponse] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const data = await invoke<string>('echo', { message: input });
      setResponse(data);
    } catch (err: any) {
      setResponse(`Failed: ${err.message || err}`);
    }
  };

  return (
    <div style={{ padding: 40, maxWidth: 600, margin: '0 auto' }}>
      <h1>Sloth Agent</h1>
      <p style={{ color: '#666' }}>Phase 0: Communication Loop Test</p>

      <form onSubmit={handleSubmit} style={{ marginTop: 24 }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Enter your requirement..."
          rows={4}
          style={{ width: '100%', padding: 12, fontSize: 14 }}
        />
        <button
          type="submit"
          style={{
            marginTop: 12,
            padding: '8px 24px',
            fontSize: 14,
            cursor: 'pointer',
          }}
        >
          Send to Backend
        </button>
      </form>

      {response && (
        <div
          style={{
            marginTop: 24,
            padding: 16,
            background: '#f5f5f5',
            borderRadius: 8,
          }}
        >
          <strong>Backend Response:</strong>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{response}</pre>
        </div>
      )}
    </div>
  );
}

export default App;
