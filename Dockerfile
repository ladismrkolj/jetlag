# Multi-stage build for Next.js app with Python backend helper
FROM node:20-alpine AS builder
WORKDIR /app

# Install frontend deps and build
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci
COPY frontend ./frontend
RUN cd frontend && npm run build

FROM node:20-alpine AS runner
WORKDIR /app

# Install Python for CLI used by API route
RUN apk add --no-cache python3

# Copy built app and production deps
COPY --from=builder /app/frontend/.next /app/frontend/.next
COPY --from=builder /app/frontend/package*.json /app/frontend/
RUN cd /app/frontend && npm ci --omit=dev

# Include python module alongside frontend (API route runs `python3 -m jetlag_core.cli`)
COPY jetlag_core /app/jetlag_core

ENV NODE_ENV=production
EXPOSE 3000
WORKDIR /app/frontend

# Start Next.js (listen on 3000)
CMD ["npm", "start", "--", "-p", "3000"]

