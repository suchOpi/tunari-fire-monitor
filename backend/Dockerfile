FROM python:3.13-slim
WORKDIR /project/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY data/geo/ /project/data/geo/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
