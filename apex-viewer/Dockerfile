# APEX Design Explorer — nginx serving the static Vite build on port 8080.
#
# The design data is BAKED into the image at build time from the committed
# all_workflows.zip, so the image is self-contained: Skiff (and `docker run`) just
# start it, no volumes or flags needed. A workflows JSONL mounted at runtime
# overrides the baked data (handy for swapping data locally without a rebuild).
#
# Build from the REPO ROOT (so the corpus zip is in the build context):
#   docker build -f apex-viewer/Dockerfile -t apex-viewer .
#   docker run --rm -p 8080:8080 apex-viewer                      # baked data, no flags
#   docker run --rm -p 8080:8080 \                                # override with fresh data
#     -v "$PWD/all_workflows.jsonl:/data/all_workflows.jsonl:ro" apex-viewer
#   # -> http://localhost:8080

# --- stage 1: build the static app WITH baked-in data -----------------------
FROM node:24-alpine AS build
WORKDIR /app
RUN apk add --no-cache unzip
COPY apex-viewer/package.json apex-viewer/package-lock.json ./
# `npm install`, not `npm ci`: the lockfile is generated on the dev's platform, but
# Vite's native deps (oxc/rolldown) pull different optional packages on linux/alpine.
RUN npm install --no-audit --no-fund
COPY apex-viewer/ ./
# Generate public/data/ from the committed corpus, then `npm run build` bakes it into dist/.
COPY all_workflows.zip ./all_workflows.zip
RUN unzip -q all_workflows.zip -d /tmp \
    && DESIGNS_JSONL=/tmp/all_workflows.jsonl npm run export \
    && rm -f all_workflows.zip /tmp/all_workflows.jsonl
RUN npm run build

# --- stage 2: nginx + node; serve baked data, or re-export a mounted JSONL ---
FROM nginx:alpine
RUN apk add --no-cache nodejs
COPY apex-viewer/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
# The export script only uses Node built-ins, so no node_modules are needed at runtime.
COPY apex-viewer/scripts/export-data.mjs /app/export-data.mjs
COPY apex-viewer/docker-prepare-data.sh /docker-entrypoint.d/40-apex-prepare-data.sh
RUN chmod +x /docker-entrypoint.d/40-apex-prepare-data.sh
EXPOSE 8080
