FROM python:3.13-slim
WORKDIR /app
ENV PORT=8000 FLOOR_DATA=/data PYTHONDONTWRITEBYTECODE=1
COPY server.py ./
COPY web ./web
RUN mkdir -p /data && useradd --system --uid 10001 floor && chown floor /data
USER floor
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"
CMD ["python", "server.py"]
