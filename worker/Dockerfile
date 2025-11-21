# worker/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# copy full repo into container so utils/ and other modules are present
COPY . /app

# install deps (use root requirements.txt)
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app

# expose port 8000 for Cloud Run
CMD ["uvicorn", "worker.worker_app:app", "--host", "0.0.0.0", "--port", "8000"]
