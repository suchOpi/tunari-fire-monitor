FROM node:22-alpine AS build
WORKDIR /project/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
COPY data/geo/ /project/data/geo/
ARG VITE_CARTO_API_KEY=
ENV VITE_CARTO_API_KEY=$VITE_CARTO_API_KEY
RUN npm run build
FROM nginx:1.27-alpine
COPY --from=build /project/frontend/dist /usr/share/nginx/html
COPY infra/nginx/nginx.conf /etc/nginx/conf.d/default.conf
