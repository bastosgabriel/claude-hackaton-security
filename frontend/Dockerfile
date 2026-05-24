FROM node:22-alpine

ENV PNPM_HOME=/pnpm \
    PATH="/pnpm:$PATH"

RUN corepack enable && corepack prepare pnpm@8.15.9 --activate

WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

EXPOSE 3000

CMD ["pnpm", "dev", "--hostname", "0.0.0.0"]
