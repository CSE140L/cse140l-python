# Use an official uv runtime as a parent image
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set the working directory in the container
WORKDIR /app

# Copy the project files into the container
COPY . .

# Install the project and its dependencies using uv
# This command reads the pyproject.toml file and installs the project in editable mode.
RUN uv pip install --system .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable for the auth token with a default value
# It's recommended to override this in docker-compose.yml
ENV REPORT_SERVER_AUTH_TOKEN="SUPER_SECRET_TOKEN"

# Run the app using gunicorn
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:1407", "report_server.report_server:app"]
