FROM node:24-bookworm-slim AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_PUBLISHABLE_KEY

ENV VITE_API_URL=/api
ENV VITE_LOCAL_DEV_MODE=false

RUN test -n "$VITE_SUPABASE_URL" \
    && test -n "$VITE_SUPABASE_PUBLISHABLE_KEY" \
    && npm run build

FROM nginx:stable-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80