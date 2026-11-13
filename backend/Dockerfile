FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /usr/src/flor-vida
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY tests ./tests
RUN useradd --create-home --uid 10001 flor && chown -R flor:flor /usr/src/flor-vida
USER flor
EXPOSE 8000
CMD ["uvicorn", "app.gateway:app", "--host", "0.0.0.0", "--port", "8000"]
