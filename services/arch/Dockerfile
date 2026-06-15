# Build stage
FROM node:22-alpine AS builder
WORKDIR /app
COPY services/arch/package.json ./
RUN npm install
COPY services/arch/ ./
RUN npm run build

# Serve stage
FROM nginx:alpine
COPY services/arch/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
