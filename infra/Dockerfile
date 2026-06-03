# Stage 1: Build
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --user --no-cache-dir .

# Stage 2: Runtime
FROM python:3.11-slim

# Create a non-root user and group
RUN groupadd -r appgroup && useradd -r -g appgroup -m appuser

WORKDIR /app

# Copy only the installed python packages from the builder stage
COPY --from=builder /root/.local /home/appuser/.local
COPY . .

# Ensure the appuser can access the installed packages
ENV PATH=/home/appuser/.local/bin:$PATH

# Change ownership of the app directory to the non-root user
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]