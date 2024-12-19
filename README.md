# URL Encoding Proxy for OCLC Discovery

## Overview
This proxy service addresses an integration challenge between OCLC Discovery and OpenAthens authentication. It properly encodes remote database search URLs from OCLC Discovery to ensure compatibility with OpenAthens authentication flows.

## Quick Start

### Prerequisites
1. Install required software:
   - Python 3.9+ (`python --version` to check)
   - [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
   - [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)

### Local Development Setup
```cmd
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
copy example.env .env
# Edit .env with your settings

# Run locally
python main.py
```

## Deployment Guide

### Initial Setup
1. Ensure you have a Google Cloud project created
2. Install and initialize Google Cloud SDK
3. Install Docker Desktop
4. Configure your .env file

### Deployment Script Usage
The `deploy.bat` script handles the entire deployment process. It has three optional parameters:

```cmd
deploy.bat [PROJECT_ID] [IMAGE_NAME] [SERVICE_NAME]
```

- `PROJECT_ID`: Your Google Cloud project ID (required)
- `IMAGE_NAME`: Name for your Docker image (optional, defaults to "url-proxy")
- `SERVICE_NAME`: Name for your Cloud Run service (optional, defaults to "url-encoder")

#### Examples:

```cmd
# Basic deployment with default values
deploy.bat my-project-id

# Custom image and service names
deploy.bat my-project-id my-custom-proxy my-custom-service

# Custom image name only
deploy.bat my-project-id my-custom-proxy
```

### What the Deployment Script Does
1. Verifies required tools are installed
2. Enables necessary Google Cloud APIs
3. Configures Docker authentication
4. Creates an Artifact Registry repository
5. Builds and tags your Docker image
6. Pushes the image to Artifact Registry
7. Deploys the service to Cloud Run

### Post-Deployment Steps
1. Update your .env file with the new Cloud Run service URL
2. Test the deployment with your OCLC Discovery instance
3. Configure monitoring and alerts in Google Cloud Console

## Configuration

### Environment Variables
Create a `.env` file based on `example.env`:

```plaintext
# Environment configuration
FLASK_ENV=production
FLASK_DEBUG=False

# Proxy domain configuration (Cloud Run service URL)
PROXY_DOMAIN=your-service-url.run.app

# OCLC Discovery referrer configuration
VALID_REFERRER=your-institution.on.worldcat.org

# Valid hosts (optional additional hosts)
VALID_HOSTS=search.ebscohost.com,search.proquest.com

# OpenAthens configuration
OPENATHENS_PREFIXES={"your-institution.on.worldcat.org": "https://go.openathens.net/redirector/your-institution.edu"}
```

## Troubleshooting

### Deployment Issues
- **Error: Docker daemon not running**
  - Start Docker Desktop
  - Wait for Docker to fully initialize
  - Try again

- **Error: Not authorized to access project**
  - Run `gcloud auth login`
  - Run `gcloud config set project PROJECT_ID`
  - Verify access with `gcloud projects list`

### Runtime Issues
- **400 Bad Request**
  - Check URL format in OCLC Discovery
  - Verify VALID_HOSTS configuration

- **403 Forbidden**
  - Check VALID_REFERRER configuration
  - Verify OpenAthens prefix settings

## Support and Contributing
- Report issues on GitHub
- Follow contribution guidelines in CONTRIBUTING.md
- Review security policy in SECURITY.md

## License
MIT License - See LICENSE file for details

## Acknowledgments
This project was developed with assistance from Anthropic's Claude AI, which helped with code generation, documentation, and best practices implementation.