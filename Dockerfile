FROM public.ecr.aws/docker/library/python:3.13-slim
WORKDIR /app
COPY app.py .
USER 10001
EXPOSE 8080
CMD ["python", "-u", "app.py"]
