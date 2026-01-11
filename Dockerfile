FROM node:20-slim AS frontend-builder

WORKDIR /frontend

# Copy dashboard source
COPY bot_tracker/dashboard/package*.json ./
RUN npm install

COPY bot_tracker/dashboard/ ./
RUN npm run build

# Python backend
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY bot_tracker_v2/ ./bot_tracker_v2/
COPY data/ ./data/
COPY run.py ./

# Copy built frontend
COPY --from=frontend-builder /frontend/dist ./static/

# Create directories
RUN mkdir -p logs data/backups

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "-m", "bot_tracker_v2"]
