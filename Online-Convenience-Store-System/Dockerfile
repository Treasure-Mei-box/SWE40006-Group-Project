FROM python:3.10-slim
WORKDIR /app

# Copy requirements from the subfolder into the container working directory
COPY Online-Convenience-Store-System/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files from the subfolder into the container
COPY Online-Convenience-Store-System/ .

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]