# GitHub Actions Workflows

This directory contains CI/CD workflows for building, pushing, and deploying the SRE Agent application.

## Workflows

### 1. Build and Push Docker Images and Helm Charts

**File:** `.github/workflows/build-and-push.yml`

**Triggers:**
- Push to `main` branch
- Version tags (e.g., `v1.0.0`, `v2.1.3`)
- Manual trigger via `workflow_dispatch`

**What it does:**
1. Builds three Docker images:
   - `sreagent` (backend service)
   - `cluster-inventory` (cluster inventory service)
   - `sreagent-frontend` (React frontend)
2. Pushes images to GitHub Container Registry (GHCR):
   - `ghcr.io/<org>/kekaflow/sreagent:<tag>`
   - `ghcr.io/<org>/kekaflow/cluster-inventory:<tag>`
   - `ghcr.io/<org>/kekaflow/sreagent-frontend:<tag>`
3. Packages and pushes Helm charts to OCI registry:
   - `oci://ghcr.io/<org>/kekaflow-charts/sreagent:<version>`
   - `oci://ghcr.io/<org>/kekaflow-charts/cluster-inventory:<version>`

**Image Tags:**
- Short commit SHA (e.g., `abc1234`) - for main branch
- `latest` - for main branch
- Semantic version tags (if version tag pushed)

### 2. Deploy to Production (Manual)

**File:** `.github/workflows/deploy-production.yml`

**Triggers:**
- Manual trigger only (`workflow_dispatch`)

**Inputs:**
- `image_tag`: Image tag to deploy (default: `latest`)
- `environment`: Environment to deploy to (`prod` or `staging`)
- `namespace`: Kubernetes namespace (default: `sreagent`)
- `release_name`: Helm release name (default: `sreagent`)

**What it does:**
1. Configures kubectl with OCI Kubernetes cluster
2. Creates imagePullSecret for GHCR authentication
3. Deploys `cluster-inventory` Helm chart
4. Deploys `sreagent` Helm chart (includes frontend)
5. Verifies all deployments are healthy

## Required Secrets

Add these secrets in your GitHub repository settings:

### For Build Workflow:
- `GITHUB_TOKEN` - Automatically provided by GitHub Actions

### For Deploy Workflow:
- `OCI_KUBECONFIG` - Your OCI Kubernetes cluster kubeconfig file content

## Usage

### Building Images

Images are automatically built when you:
- Push to `main` branch
- Create and push a version tag: `git tag v1.0.0 && git push origin v1.0.0`

### Manual Deployment

1. Go to GitHub Actions tab
2. Select "Deploy to Production (OCI Kubernetes)"
3. Click "Run workflow"
4. Fill in the inputs:
   - **Image tag**: Use commit SHA (e.g., `abc1234`) or `latest`
   - **Environment**: `prod` or `staging`
   - **Namespace**: `sreagent` (or your target namespace)
   - **Release name**: `sreagent` (or your release name)
5. Click "Run workflow"

### Finding Image Tags

After a build completes, you can find the image tags:
- In the workflow run summary
- In GitHub Container Registry: `https://github.com/<org>?tab=packages`
- Using the short commit SHA from the commit that triggered the build

## Image Names

The workflows use the same image names as local development:
- `sreagent` - Backend service
- `cluster-inventory` - Cluster inventory service  
- `sreagent-frontend` - Frontend service

Images are pushed to: `ghcr.io/<org>/kekaflow/<image-name>:<tag>`

## Helm Charts

Helm charts are packaged and pushed to OCI registry:
- `oci://ghcr.io/<org>/kekaflow-charts/sreagent:<version>`
- `oci://ghcr.io/<org>/kekaflow-charts/cluster-inventory:<version>`

Chart versions follow pattern: `0.1.0-<commit-sha>`

