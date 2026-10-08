FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt requirements.ml.txt ./
RUN pip install --no-cache-dir -r requirements.ml.txt
ENV PYTHONPATH=/app
ENTRYPOINT ["python", "-m", "src.ml"]
