FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY persona.example.md .
RUN useradd -m agent && mkdir /data /srv/custom_skills && chown agent /data
USER agent
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
