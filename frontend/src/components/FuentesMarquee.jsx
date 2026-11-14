const FUENTES = ['NASA FIRMS', 'MODIS', 'VIIRS NOAA-20', 'VIIRS NOAA-21', 'GAMC Cochabamba', 'OpenStreetMap', 'PostGIS'];

export default function FuentesMarquee() {
  return <section className="sources-marquee" aria-label="Fuentes de datos">
    <div className="marquee-track" aria-hidden="true">{[...FUENTES, ...FUENTES].map((nombre, i) => <span key={i}>{nombre}</span>)}</div>
    <ul className="visually-hidden">{FUENTES.map((nombre) => <li key={nombre}>{nombre}</li>)}</ul>
  </section>;
}
