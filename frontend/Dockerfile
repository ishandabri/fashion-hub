FROM node:22-alpine AS build
WORKDIR /app
ARG APP_VERSION=0.1.0
ARG APP_REVISION=dev
ARG APP_BUILT_AT=development
ENV APP_VERSION=$APP_VERSION APP_REVISION=$APP_REVISION APP_BUILT_AT=$APP_BUILT_AT
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --no-frozen-lockfile --prod=false
COPY . .
RUN pnpm build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80

