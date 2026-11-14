import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { FiltrosProvider } from './context/FiltrosContext';
import 'leaflet/dist/leaflet.css';
import './index.css';
import './redesign.css';
import './theme.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode><FiltrosProvider><App /></FiltrosProvider></React.StrictMode>,
);
