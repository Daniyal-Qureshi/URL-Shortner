FROM python:3.11

WORKDIR /src

COPY ./requirements.txt /src/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /src/requirements.txt

COPY . /src

CMD ["fastapi", "run", "app.py", "--proxy-headers", "--port", "80"]
