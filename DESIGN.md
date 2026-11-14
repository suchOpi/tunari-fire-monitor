# Design System: Tunari Fire Monitor

Documenta el sistema de diseño que **ya existe** en `frontend/src`. No propone cambios de identidad. Los valores salen de `frontend/src/tokens.css` y de las hojas `index.css`, `redesign.css` y `theme.css`.

## 1. Visual Theme & Atmosphere

Instrumento de observación sobrio y territorial: denso en información pero legible, con el mapa como protagonista. Un encabezado oscuro azul-verdoso ancla la página; el contenido vive sobre superficies claras (tema claro) o sobre azules muy oscuros (tema oscuro). Densidad media-alta, simetría funcional, movimiento mínimo y con significado. Ambos temas son de primera clase y se eligen con el botón «Vista oscura/clara» (se guarda en `localStorage`, clave `tunari-theme`).

## 2. Color Palette & Roles

Tema claro (`:root`):
- **Bruma de fondo** (#f0f2ee) `--bg`: fondo de página
- **Superficie** (#ffffff) `--panel`: paneles y tarjetas
- **Tinta profunda** (#183138) `--ink`: texto principal
- **Gris verdoso de apoyo** (#566863) `--muted`: texto secundario, ≥4.9:1 sobre sus fondos
- **Línea suave** (#d9e1dc) `--line`: bordes y separadores de 1px
- **Verde azulado de acento** (#087f80) `--accent`: acciones, selección y foco
- **Bosque** (#3c744c) `--green`, **Arcilla** (#a45c34) `--orange`, **Ladrillo** (#b54842) `--red`: significado semántico (estado y nivel de alerta)

Tema oscuro (`html[data-theme=dark]`):
- Fondo #0d1b21, panel #152a31, línea #354c50, muted #a9bfba, acento #75d7c4, verde #acd29d, naranja #e4b089, rojo #eeaaa1, tinta #e5efea

Encabezado (ambos temas): fondo #132d36, texto #f4f8f2, acento de marca #69dfd4.

Regla: el color significa estado (nivel de alerta, frescura de la fuente), no decoración. El estado nunca se comunica solo con color.

## 3. Typography Rules

- **Titulares:** Manrope (`--font-display`), pesos 500–800, tracking ligeramente negativo.
- **Cuerpo e interfaz:** DM Sans (`--font-body`); `--ui` (Segoe UI / system-ui) en etiquetas y datos.
- **Mono:** `--mono` (ui-monospace) para metadatos.
- **Cifras:** `font-variant-numeric: tabular-nums` en KPIs y métricas.
- **Mínimo:** 11px en cualquier texto. Prosa a 65–75ch como máximo.
- Los titulares usan `text-wrap: balance`.

## 4. Component Stylings

- **Botones:** borde de 1px, radio 7–8px; hover cambia fondo y borde; `:active` baja 1px; foco visible de 3px en #00aaa9. Altura mínima 44px por debajo de 900px de ancho.
- **Tarjetas de distrito y alerta:** borde fino; en hover suben 1px con sombra teñida por el acento; seleccionadas usan `aria-pressed`.
- **Paneles de informe:** radio 13px, borde #d6dfd1 (claro), fondos propios por tema.
- **Controles de formulario:** etiqueta encima, `select` y `input[type=date]` de 40–44px.
- **Gráficas:** SVG propio con barras por sensor (lila, verde, naranja); el calendario usa un cian cuya opacidad sube con el conteo (escala menor en oscuro para mantener contraste).
- **Estados de datos:** «Sin dato», «Parcial», «Atrasado» y «Sin actualización» son estados visibles, nunca se ocultan.

## 5. Layout Principles

- Cuadrícula de dos columnas en el espacio de trabajo: barra lateral 335–405px + mapa; en móvil (≤640px) pasa a una columna con la barra lateral desplegada en orden.
- Contenedor del encabezado limitado a ~1456px; el resto se adapta al ancho.
- Puntos de corte usados: 1700, 1250, 1200, 1100, 1000, 900, 850, 640 y 600px.
- Sin scroll horizontal en 320–1920px. La app usa `min-height: 100dvh`.
- Objetivos táctiles: 24–28px mínimo en escritorio, 44px bajo 900px.

## 6. Motion & Interaction

- Easing único: `--ease-out` = `cubic-bezier(0.16, 1, 0.3, 1)`; transiciones de 160–200ms.
- Solo `transform` y `opacity`. Entrada de paneles de informe con `animation-timeline: view()` (dentro de `@supports`), con opacidad mínima 0.55 para que nunca queden ocultos.
- `prefers-reduced-motion: reduce` apaga transiciones y animaciones.
- Actualización automática cada 60s, en pausa mientras la pestaña está oculta.

## 7. Anti-Patterns (Banned)

- Mostrar datos simulados o inventar clasificaciones; la interfaz no tiene fallback a mocks.
- Comunicar estado solo con color.
- Texto menor de 11px o con contraste menor de 4.5:1.
- Animaciones decorativas, orquestaciones de carga y movimiento de propiedades de layout.
- Imágenes de stock, emojis como iconos y gradientes decorativos.

## 8. Known gaps

- Cientos de colores hex siguen escritos a mano en `index.css`, `redesign.css` y `theme.css`; solo la paleta base está en tokens.
- Tres hojas de estilo conviven (`index.css`, `redesign.css`, `theme.css`) y solo los tokens están unificados.
- La etiqueta del parque sobre el mapa se oculta en móvil porque chocaba con el título del mapa.
