FROM node:20-alpine

WORKDIR /app

# Install dependencies
RUN apk add --no-cache libc6-compat

# Copy package files
COPY package.json package-lock.json* ./
RUN npm ci

# Copy application code
COPY . .

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

# For development, use dev server (override in docker-compose)
CMD ["npm", "run", "dev"]
