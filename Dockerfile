# Stage 1: Build Vite assets
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve static files via Nginx
FROM nginx:1-alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Optional: add a custom nginx.conf if routing rules are needed.
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
