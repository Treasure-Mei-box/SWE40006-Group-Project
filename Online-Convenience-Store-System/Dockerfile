FROM python:3.10-slim
WORKDIR /app

# Copy requirements file from the build context
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files from the build context
COPY . .
ARG GIT_SHA=unknown
ENV GIT_SHA=$GIT_SHA

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
#CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:demoapp"]