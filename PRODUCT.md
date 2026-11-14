# Product

## Register

product

## Users

Personal técnico y de gestión de riesgo del municipio de Cercado (Cochabamba, Bolivia) y ciudadanía interesada en el Parque Nacional Tunari. Consultan el panel para saber si hubo detecciones satelitales de calor recientes, en qué distrito, y cómo se compara con el historial. Suelen estar bajo presión de tiempo durante la temporada de incendios y pueden estar en móvil o en una pantalla de oficina.

## Product Purpose

Observatorio local que reúne detecciones NASA FIRMS (MODIS y VIIRS), límites territoriales del GAMC y registros históricos en PostGIS, para mostrar qué se detectó, dónde y con qué cobertura. Nunca presenta datos simulados ni inventa clasificaciones: cuando falta un dato, lo dice y explica por qué. El éxito es que una persona entienda en segundos el estado actual y sepa cuánta confianza darle.

## Brand Personality

Sobrio, honesto, territorial. Tono de instrumento científico cercano: preciso sin ser frío, en español claro, con incertidumbre explícita («Sin detecciones ≠ sin fuego»).

## Anti-references

- Paneles de seguridad "alarmistas" en rojo saturado con sirenas e iconos de fuego decorativos.
- Dashboards SaaS genéricos de tarjetas idénticas con métricas gigantes.
- Imágenes de stock o ilustraciones que sustituyan datos reales.
- Cualquier elemento que sugiera certeza oficial donde los datos son parciales o ilustrativos.

## Design Principles

1. La honestidad del dato manda: estados «sin dato», «parcial» y «atrasado» son ciudadanos de primera, nunca se ocultan ni se maquillan.
2. El mapa es el protagonista; el resto lo acompaña y lo filtra.
3. Legible bajo estrés: jerarquía clara, texto cómodo de leer y contraste alto, también en móvil.
4. Familiaridad antes que sorpresa: patrones de navegación y controles estándar, consistentes entre secciones.
5. El color significa algo: nivel de alerta y estado de la fuente, no decoración.

## Accessibility & Inclusion

Objetivo WCAG 2.2 AA: contraste 4.5:1 en texto normal, foco visible, navegación por teclado, `prefers-reduced-motion` respetado, y el estado nunca se comunica solo con color. Interfaz en español; probar de 320 px a 1920 px y en ambos temas (claro y oscuro).

> Borrador inferido del README y de los documentos del repo (propósito, usuarios, personalidad y anti-referencias no estaban escritos de forma explícita). Ajústalo si algo no coincide con tu intención.
