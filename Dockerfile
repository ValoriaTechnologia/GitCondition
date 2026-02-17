FROM python:3-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY main.py /main.py
ENTRYPOINT ["python3", "/main.py"]
