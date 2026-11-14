const paths = {
  map: 'M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3V6z M9 3v15 M15 6v15',
  chart: 'M4 3v17h17 M8 16v-5 M13 16V6 M18 16V9',
  brain: 'M12 4a3 3 0 0 0-5-1 4 4 0 0 0-3 6 4 4 0 0 0 0 7 4 4 0 0 0 8 2V4z M12 4a3 3 0 0 1 5-1 4 4 0 0 1 3 6 4 4 0 0 1 0 7 4 4 0 0 1-8 2 M7 7c0 2 2 3 5 3 M17 7c0 2-2 3-5 3 M7 16c0-2 2-3 5-3 M17 16c0-2-2-3-5-3',
  moon: 'M20.8 13.2A9 9 0 1 1 10.8 3.1a7 7 0 0 0 10 10.1z',
  sun: 'M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M12 2v2 M12 20v2 M2 12h2 M20 12h2 M5 5l1.5 1.5 M17.5 17.5L19 19 M5 19l1.5-1.5 M17.5 6.5L19 5',
  refresh: 'M20 7a9 9 0 0 0-15-2L2 8 M2 3v5h5 M4 17a9 9 0 0 0 15 2l3-3 M22 21v-5h-5',
  external: 'M14 3h7v7 M21 3L10 14 M10 3H4a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1v-6',
  target: 'M19 12a7 7 0 1 1-14 0 7 7 0 0 1 14 0 M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0 M12 2v3 M12 19v3 M2 12h3 M19 12h3',
  alert: 'M10.3 3.9 2.2 18a2 2 0 0 0 1.7 3h16.2a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z M12 9v4 M12 17h.01',
  history: 'M3 11a9 9 0 1 1 2.6 7 M3 4v7h7 M12 7v5l3 2',
  layers: 'M12 3 2 8l10 5 10-5-10-5z M2 12l10 5 10-5 M2 16l10 5 10-5',
  chevron: 'M6 9l6 6 6-6',
  tree: 'M12 2 6 9h3l-5 6h4l-5 5h18l-5-5h4l-5-6h3l-6-7z M12 20v3',
  filter: 'M4 6h16 M4 12h16 M4 18h16 M8 3v6 M16 9v6 M10 15v6',
  calendar: 'M5 5h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z M7 3v4 M17 3v4 M3 11h18 M7 15h2 M13 15h2 M7 18h2',
  database: 'M21 5c0 2-4 3-9 3S3 7 3 5s4-3 9-3 9 1 9 3z M3 5v14c0 2 4 3 9 3s9-1 9-3V5 M3 12c0 2 4 3 9 3s9-1 9-3',
  download: 'M12 3v12 M7 10l5 5 5-5 M4 15v5h16v-5',
  file: 'M14 2H5v20h14V7l-5-5z M14 2v5h5 M8 12h8 M8 16h8',
  printer: 'M6 9V3h12v6 M6 17H3V9h18v8h-3 M6 14h12v8H6v-8z M17 12h.01',
  search: 'M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0 M15 15l6 6',
  check: 'M5 12l4 4L19 6',
  info: 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0 M12 11v6 M12 7h.01',
  clock: 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0 M12 6v6l4 2',
  grid: 'M3 3h7v7H3V3z M14 3h7v7h-7V3z M3 14h7v7H3v-7z M14 14h7v7h-7v-7z',
  radar: 'M22 12a10 10 0 1 1-10-10 M18 12a6 6 0 1 1-6-6 M14 12a2 2 0 1 1-2-2 M12 12 21 3',
  eye: 'M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
  plus: 'M12 5v14 M5 12h14',
  minus: 'M5 12h14',
};

export default function Icon({ name, size = 18, className = '' }) {
  return <svg className={`ui-icon ${className}`} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false"><path d={paths[name] || paths.info} /></svg>;
}

export function createIconElement(name) {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  for (const [key, value] of Object.entries({class:'ui-icon', width:18, height:18, viewBox:'0 0 24 24', fill:'none', stroke:'currentColor', 'stroke-width':1.7, 'stroke-linecap':'round', 'stroke-linejoin':'round', 'aria-hidden':'true', focusable:'false'})) svg.setAttribute(key, value);
  const path = document.createElementNS(ns, 'path'); path.setAttribute('d', paths[name] || paths.info); svg.append(path);
  return svg;
}
