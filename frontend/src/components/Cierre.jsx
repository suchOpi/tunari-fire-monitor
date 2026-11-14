import Icon from './Icon';

export default function Cierre() {
  return <section className="closing" aria-labelledby="closing-title">
    <h2 id="closing-title">Una señal satelital requiere contexto.<br /><span>Sin detecciones ≠ sin fuego.</span></h2>
    <a className="cta cta-primary" href="#territorio"><Icon name="map" size={18} />Volver al mapa</a>
  </section>;
}
