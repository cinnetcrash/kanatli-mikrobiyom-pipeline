FROM python:3.11-slim

LABEL maintainer="Kanatlı Mikrobiyom Pipeline"
LABEL description="İstatistiksel analiz Docker imajı - Pandas, Matplotlib, SciPy"

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

COPY docker/stats/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY scripts/ /scripts/
RUN chmod +x /scripts/*.py

WORKDIR /data

CMD ["python", "/scripts/abundance_analysis.py", "--help"]
