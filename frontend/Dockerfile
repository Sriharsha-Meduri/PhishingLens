# Frontend dev/preview image (build context = ./frontend)
FROM node:20-alpine
WORKDIR /app
COPY package.json ./
RUN npm install --no-audit --no-fund
COPY . .
# Point the SPA at the API. Overridden per-environment (Vercel uses VITE_API_URL).
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
