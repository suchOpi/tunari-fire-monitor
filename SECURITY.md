# Seguridad

## Cómo reportar una vulnerabilidad

No abras un issue público. Usa **Security > Report a vulnerability** en este repositorio de GitHub
(reporte privado). Incluye los pasos para reproducirla y el impacto.

## Secretos

- Las llaves y contraseñas viven solo en variables de entorno o en archivos `.env` que **no** se versionan
  (`.gitignore` los excluye). `.env.example` solo trae marcadores como `CAMBIA_ESTA_CLAVE`.
- Si crees que una llave se filtró, revócala en su proveedor y genera otra: borrar el commit no basta.
- Las variables `VITE_*` terminan dentro del JavaScript público. No pongas ahí secretos.
  Si usas una llave de CARTO, restríngela por dominio en su panel.

## Modificación de alertas

`PATCH /api/alertas/{id}` y `POST /api/alertas/{id}/confirmar` exigen un token de operador (`API_TOKEN`).
Sin `API_TOKEN` configurado, la escritura queda deshabilitada.

## Despliegue

El backend y PostGIS no deben exponerse a internet sin HTTPS, límite de peticiones y un proxy inverso.
