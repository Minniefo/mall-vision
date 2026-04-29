FROM python:3.10-slim

# Install system dependencies for OpenCV, MTCNN, and AI libraries
# libgl1-mesa-glx and libglib2.0-0 are specifically required by OpenCV
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirement files and install dependencies
# We use no-cache-dir to keep the image size smaller
COPY requirements-base.txt .
COPY requirements-ai.txt .
RUN pip install --no-cache-dir -r requirements-base.txt
RUN pip install --no-cache-dir -r requirements-ai.txt


# Copy the entire backend source code
COPY . .

# Move insightface models to the expected location in the container
# This looks for .insightface in either the root or the backend folder
RUN mkdir -p /root/.insightface && \
    if [ -d "age-gender-backend/.insightface" ]; then cp -r age-gender-backend/.insightface/* /root/.insightface/; \
    elif [ -d ".insightface" ]; then cp -r .insightface/* /root/.insightface/; fi

# Expose FastAPI port
EXPOSE 8000

# Run uvicorn server (Assuming main.py is your entrypoint)
# In production on a limited machine, keeping workers to 1 is important
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
