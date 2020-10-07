FROM python:3.7
EXPOSE 8000
COPY . /
WORKDIR /
RUN apt-get update -y && apt-get install redis  libpython-dev -y
RUN pip3 install -r requirements.txt 
CMD chmod +x start.sh && ./start.sh