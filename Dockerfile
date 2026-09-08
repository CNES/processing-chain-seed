# Lightweight image with the geospatial dependencies required by rasterio
FROM python:3.11-slim

LABEL description="NDWI processing chain from Sentinel-2 bands"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libexpat1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/compute_ndwi.py .

CMD ["python3", "/app/compute_ndwi.py"]
