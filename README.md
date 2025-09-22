# mcp-server


# Build image
docker build -t mcp-ci-generator:latest .

# Run container
docker run -d -p 5000:5000 -e GITHUB_TOKEN=ghp_xxx ci-generator:latest
