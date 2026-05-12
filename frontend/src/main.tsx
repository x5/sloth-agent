import React from 'react';
import ReactDOM from 'react-dom/client';

import { initBackendUrl } from './api/client';
import App from './App';

async function main() {
  await initBackendUrl();
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
}

main();
