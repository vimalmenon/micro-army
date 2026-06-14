# Build stage
FROM node:22-alpine AS builder
ARG VITE_HESTIA_API_KEY
ENV VITE_HESTIA_API_KEY=$VITE_HESTIA_API_KEY
WORKDIR /app
COPY services/helios/package.json ./
RUN npm install
COPY services/helios/ .
RUN npm run build

# Serve stage
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
