# Stage 1: build the website
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY . .
# Empty = the website and the API share one address (the Caddy setup below)
ARG VITE_API_URL=""
ARG VITE_CONTACT_EMAIL=""
ARG VITE_CONTACT_PHONE=""
ARG VITE_CONTACT_WHATSAPP=""
ENV VITE_API_URL=$VITE_API_URL VITE_CONTACT_EMAIL=$VITE_CONTACT_EMAIL VITE_CONTACT_PHONE=$VITE_CONTACT_PHONE VITE_CONTACT_WHATSAPP=$VITE_CONTACT_WHATSAPP
RUN npm run build

# Stage 2: Caddy serves the website, forwards /api and /uploads to the backend, and gets HTTPS certificates automatically
FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
