FROM --platform=linux/amd64 python:3.9-slim

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy code into container
COPY . .

# Run the main script
CMD ["python", "main.py"]
