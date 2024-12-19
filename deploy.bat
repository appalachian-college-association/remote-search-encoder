@echo off
REM Windows deployment script for Cloud Run
REM Usage: deploy.bat [PROJECT_ID] [IMAGE_NAME] [SERVICE_NAME]

REM Check if project ID was provided
IF "%~1"=="" (
    echo Error: Project ID is required
    echo Usage: deploy.bat [PROJECT_ID] [IMAGE_NAME] [SERVICE_NAME]
    echo Example: deploy.bat my-project-id my-proxy my-service
    exit /b 1
)

REM Set variables with defaults
set PROJECT_ID=%1

IF "%~2"=="" (
    echo Using default image name: url-proxy
    set IMAGE_NAME=url-proxy
) else (
    set IMAGE_NAME=%2
)

IF "%~3"=="" (
    echo Using default service name: url-encoder
    set SERVICE_NAME=url-encoder
) else (
    set SERVICE_NAME=%3
)

REM Verify Google Cloud CLI installation
where gcloud >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Error: Google Cloud CLI (gcloud) not found
    echo Please install from: https://cloud.google.com/sdk/docs/install
    exit /b 1
)

REM Verify Docker installation
where docker >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Error: Docker not found
    echo Please install Docker Desktop from: https://www.docker.com/products/docker-desktop
    exit /b 1
)

echo Enabling required APIs...
call gcloud services enable artifactregistry.googleapis.com
call gcloud services enable run.googleapis.com
call gcloud services enable cloudbuild.googleapis.com

echo Configuring Docker authentication...
call gcloud auth configure-docker us-central1-docker.pkg.dev
IF %ERRORLEVEL% NEQ 0 (
    echo Error: Docker authentication failed
    exit /b 1
)

echo Creating Artifact Registry repository...
call gcloud artifacts repositories create url-proxy-repo ^
    --repository-format=docker ^
    --location=us-central1 ^
    --description="URL Encoder Proxy repository"
IF %ERRORLEVEL% NEQ 0 (
    echo Note: Repository might already exist, continuing...
)

echo Building Docker image...
docker build -t %IMAGE_NAME% .
IF %ERRORLEVEL% NEQ 0 (
    echo Error: Docker build failed
    exit /b 1
)

echo Tagging image for Artifact Registry...
docker tag %IMAGE_NAME% us-central1-docker.pkg.dev/%PROJECT_ID%/url-proxy-repo/%IMAGE_NAME%:v1
IF %ERRORLEVEL% NEQ 0 (
    echo Error: Docker tag failed
    exit /b 1
)

echo Pushing image to Artifact Registry...
docker push us-central1-docker.pkg.dev/%PROJECT_ID%/url-proxy-repo/%IMAGE_NAME%:v1
IF %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to push image to Artifact Registry
    exit /b 1
)

echo Deploying to Cloud Run...
call gcloud run deploy %SERVICE_NAME% ^
    --image us-central1-docker.pkg.dev/%PROJECT_ID%/url-proxy-repo/%IMAGE_NAME%:v1 ^
    --platform managed ^
    --region us-central1 ^
    --allow-unauthenticated

IF %ERRORLEVEL% NEQ 0 (
    echo Error: Deployment failed
    exit /b 1
)

echo Deployment completed successfully!
echo Review your deployment in the Google Cloud Console

pause