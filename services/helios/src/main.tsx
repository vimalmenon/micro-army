import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { HeliosDataProvider } from './context/HeliosDataContext';
import './index.css';

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('Root element not found');
}

createRoot(rootElement).render(
  <StrictMode>
    <BrowserRouter>
      <HeliosDataProvider>
        <App />
      </HeliosDataProvider>
    </BrowserRouter>
  </StrictMode>
);
