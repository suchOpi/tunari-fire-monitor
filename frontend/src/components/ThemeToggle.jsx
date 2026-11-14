import { useLayoutEffect, useState } from 'react';
import Icon from './Icon';

export default function ThemeToggle() {
  const [dark, setDark] = useState(() => {
    try { return localStorage.getItem('tunari-theme') === 'dark'; }
    catch { return false; }
  });
  useLayoutEffect(() => {
    const theme = dark ? 'dark' : 'light';
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('tunari-theme', theme); } catch {                                                            }
  }, [dark]);
  return <button className="theme-toggle" aria-label="Vista oscura" aria-pressed={dark} title={dark ? 'Activar vista clara' : 'Activar vista oscura'} onClick={() => setDark(value => !value)}><Icon name={dark ? 'sun' : 'moon'} /><span>{dark ? 'Vista clara' : 'Vista oscura'}</span></button>;
}
