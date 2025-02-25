FROM python:3.9
RUN apt-get update && apt-get install -y google-chrome-stable chromium-driver
