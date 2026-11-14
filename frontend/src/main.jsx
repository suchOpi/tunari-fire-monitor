import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { FiltrosProvider } from './context/FiltrosContext';
import ErrorBoundary from './components/ErrorBoundary';
import 'leaflet/dist/leaflet.css';
import './tokens.css';
import './index.css';
import './redesign.css';
import './theme.css';
import './visual.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode><ErrorBoundary><FiltrosProvider><App /></FiltrosProvider></ErrorBoundary></React.StrictMode>,
);
