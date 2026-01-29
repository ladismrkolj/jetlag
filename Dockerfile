# Multi-stage build for Next.js app
FROM node:20-alpine AS builder
WORKDIR /app

# Install deps and build
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app

# Copy built app and production deps
COPY --from=builder /app/.next /app/.next
COPY --from=builder /app/package*.json /app/
RUN npm ci --omit=dev

ENV NODE_ENV=production
EXPOSE 3000
WORKDIR /app

# Start Next.js (listen on 3000)
CMD ["npm", "start", "--", "-p", "3000"]
