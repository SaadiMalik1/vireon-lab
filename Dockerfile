# Use an official lightweight Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7777

# Set the working directory
WORKDIR /app

# Install system dependencies required for Rust, scientific libraries, and weasyprint
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Rust toolchain (needed for Maturin/Runemate build)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy project files
COPY . .

# Install dependencies (installing with all optional dependencies for full feature support)
RUN pip install --no-cache-dir -e .[all]

# Create a non-root user and group
RUN groupadd -r neuroshield && useradd -r -g neuroshield -d /app neuroshield && \
    chown -R neuroshield:neuroshield /app

# Switch to the non-root user
USER neuroshield

# Expose the Web UI port
EXPOSE 7777

# Default command: Run the web UI securely on port 7777 and bind to all interfaces
CMD ["python", "-m", "neuroshield", "ui", "--port", "7777", "--host", "0.0.0.0"]
