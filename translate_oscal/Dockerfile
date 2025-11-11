# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Set environment variables (if needed, otherwise remove this section)
# ENV GCP_PROJECT_ID="your-project-id"
# ENV BUCKET_NAME="your-bucket-name"

# Command to run the application
CMD ["python", "main.py"]