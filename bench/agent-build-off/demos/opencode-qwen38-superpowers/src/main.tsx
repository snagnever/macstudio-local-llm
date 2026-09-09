import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { startRun } from './game/session';
import './ui.css';

declare global {
  interface Window {
    startHyperRun: (seedLabel?: string) => void;
  }
}

// console repro: window.startHyperRun('3F') starts a run from seed base36 '3F'
window.startHyperRun = startRun;

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
