FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HERMES_MODE=PAPER
WORKDIR /app
RUN addgroup --system hermes && adduser --system --ingroup hermes hermes
COPY . /app
RUN mkdir -p /app/data /app/logs && chown -R hermes:hermes /app
USER hermes
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD ["python","scripts/healthcheck.py"]
CMD ["python","main.py"]
