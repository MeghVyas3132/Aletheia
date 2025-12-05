# Frontend Dockerfile
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Set API URL for build time (Next.js bakes NEXT_PUBLIC_* at build)
ENV NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Build the application
RUN npm run build

# Expose port
EXPOSE 3000

# Run the application
CMD ["npm", "start"]
