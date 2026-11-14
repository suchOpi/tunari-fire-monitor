import FiltrosFecha from './FiltrosFecha';
import PanelAlertas from './PanelAlertas';
import PanelDistritos from './PanelDistritos';
import Icon from './Icon';

export default function Sidebar() {
  return <aside className="sidebar" aria-label="Controles del territorio">
    <FiltrosFecha />
    <PanelDistritos />
    <PanelAlertas />
    <div className="sidebar-foot"><span className="small-orbit"><Icon name="info" size={25} /></span><p>Una señal satelital requiere contexto.<br /><strong>Sin detecciones ≠ sin fuego.</strong></p></div>
  </aside>;
}
