# Multi-site Astro -> static -> nginx. One image, one Fly app, many sites.
# Imagery is committed to the repo (src/assets), so the build is hermetic:
# no PEXELS_API_KEY needed at deploy time.

# --- build stage ---
FROM node:24-alpine AS build
WORKDIR /app

# Canonical/JSON-LD base URL (Astro.site). Override per environment.
ARG SITE_URL=https://local-web-ka.fly.dev
ENV SITE_URL=${SITE_URL}

COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund

COPY . .
# astro build only (the npm `postbuild` validator needs uv and lives
# outside this context; the deliverable gate runs in CI/local before deploy).
RUN npx astro build

# --- runtime stage ---
FROM nginx:1.27-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
