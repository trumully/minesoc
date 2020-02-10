FROM python:3.8.1
WORKDIR /minesoc
COPY . .
RUN pip install -r requirements.txt
COPY config.json .
CMD ["python", "-m", "minesoc"]