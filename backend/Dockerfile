FROM python:3.12-slim

# Set up a new user named "user" with UID 1000 (required for Hugging Face Spaces)
RUN useradd -m -u 1000 user

# Set home and path for the user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Set the working directory
WORKDIR $HOME/app

# Copy the requirements file and install dependencies
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files (like app.py, system_prompt.md)
COPY --chown=user:user . .

# Expose port 7860 (Hugging Face Spaces expects traffic on port 7860)
EXPOSE 7860

# Run the FastAPI server using Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
