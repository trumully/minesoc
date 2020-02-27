FROM python:3.8.2

WORKDIR /usr/src/bot

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /usr/src/bot

CMD ["python", "-m", "minesoc"]