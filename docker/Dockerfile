FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY app ./app 

RUN pip install --upgrade pip
RUN pip install -e . 

CMD ["python", "--version"]