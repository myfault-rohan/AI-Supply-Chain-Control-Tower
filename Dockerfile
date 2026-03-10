FROM python:3.11

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
EXPOSE 8501

CMD ["uvicorn", "backend.api_server:app", "--host", "0.0.0.0", "--port", "8000"]
