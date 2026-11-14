import { Component } from 'react';

export default class ErrorBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(error, info) { console.error('Tunari: error de interfaz', error, info?.componentStack); }
  render() {
    if (!this.state.failed) return this.props.children;
    return <main className="error-boundary" role="alert">
      <h1>La interfaz tuvo un problema</h1>
      <p>Los datos guardados no se modificaron. Recarga la página para intentarlo de nuevo.</p>
      <button onClick={() => window.location.reload()}>Recargar</button>
    </main>;
  }
}
