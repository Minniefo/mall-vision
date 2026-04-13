# ==========================================
# Stage 1: Build the React Application
# ==========================================
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files separately to leverage Docker caching
COPY package.json package-lock.json ./
RUN npm install

# Copy project files
COPY . .

# Build the Vite application for production
RUN npm run build

# ==========================================
# Stage 2: Serve the Static Output using Nginx
# ==========================================
FROM nginx:alpine

# Copy built assets from the builder stage to Nginx web root
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80 for the frontend
EXPOSE 80

# Run Nginx
CMD ["nginx", "-g", "daemon off;"]
