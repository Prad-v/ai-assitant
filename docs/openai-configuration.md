# OpenAI Model Configuration Guide

## Overview

The SRE Agent supports both Google Gemini and OpenAI models. This guide explains how to configure OpenAI models with API key management via Kubernetes secrets.

## Configuration Options

### Model Provider Selection

The agent supports two model providers:
- **Gemini** (default): Google's Gemini models
- **OpenAI**: OpenAI models (GPT-4, GPT-3.5-turbo, etc.)

### Helm Values Configuration

#### Using Gemini (Default)

```yaml
app:
  modelProvider: "gemini"
  modelName: "gemini-2.0-flash"  # Optional, uses default if empty
```

#### Using OpenAI

```yaml
app:
  modelProvider: "openai"
  modelName: "gpt-4"  # or "gpt-4-turbo", "gpt-3.5-turbo", etc.

openai:
  createSecret: false  # Set to true to auto-create secret from apiKey
  secretName: "openai-api-key"
  secretKey: "api-key"
  apiKey: ""  # Only used if createSecret is true
```

## Creating OpenAI API Key Secret

### Method 1: Manual Secret Creation (Recommended for Production)

```bash
# Create secret manually
kubectl create secret generic openai-api-key \
  --from-literal=api-key=YOUR_OPENAI_API_KEY \
  -n sreagent

# Verify secret
kubectl get secret openai-api-key -n sreagent
```

### Method 2: Using Helm Values (Development Only)

```yaml
openai:
  createSecret: true
  secretName: "openai-api-key"
  secretKey: "api-key"
  apiKey: "sk-your-actual-api-key-here"  # NOT RECOMMENDED for production
```

**Warning**: Storing API keys directly in Helm values is not secure. Use Method 1 for production.

## Deployment Examples

### Deploy with OpenAI Model

```bash
# 1. Create the secret first
kubectl create secret generic openai-api-key \
  --from-literal=api-key=YOUR_OPENAI_API_KEY \
  -n sreagent

# 2. Deploy with OpenAI configuration
helm upgrade --install sreagent ./helm/sreagent \
  --namespace sreagent \
  --set app.modelProvider=openai \
  --set app.modelName=gpt-4 \
  --set openai.secretName=openai-api-key
```

### Deploy with Gemini Model (Default)

```bash
helm upgrade --install sreagent ./helm/sreagent \
  --namespace sreagent \
  --set app.modelProvider=gemini \
  --set app.modelName=gemini-2.0-flash
```

### Switch Between Models

```bash
# Switch to OpenAI
helm upgrade sreagent ./helm/sreagent \
  --namespace sreagent \
  --reuse-values \
  --set app.modelProvider=openai \
  --set app.modelName=gpt-4

# Switch back to Gemini
helm upgrade sreagent ./helm/sreagent \
  --namespace sreagent \
  --reuse-values \
  --set app.modelProvider=gemini \
  --set app.modelName=gemini-2.0-flash
```

## Supported Models

### OpenAI Models
- `gpt-4`
- `gpt-4-turbo`
- `gpt-3.5-turbo`
- `gpt-4o`
- `gpt-4o-mini`

### Gemini Models
- `gemini-2.0-flash`
- `gemini-1.5-pro`
- `gemini-1.5-flash`

## Environment Variables

The following environment variables are set in the deployment:

- `MODEL_PROVIDER`: "gemini" or "openai"
- `MODEL_NAME`: Specific model name (if provided)
- `GEMINI_MODEL`: Gemini model (if MODEL_NAME not set and provider is gemini)
- `OPENAI_MODEL`: OpenAI model (if MODEL_NAME not set and provider is openai)
- `OPENAI_API_KEY`: OpenAI API key (from secret, if provider is openai)

## Verification

### Check Current Configuration

```bash
# Check deployment environment variables
kubectl get deployment sreagent -n sreagent -o jsonpath='{.spec.template.spec.containers[0].env[*]}' | jq

# Check secret exists
kubectl get secret openai-api-key -n sreagent

# Check pod logs for model initialization
kubectl logs -n sreagent deployment/sreagent | grep -i "model\|openai\|gemini"
```

### Test the Agent

```bash
# Port forward
kubectl port-forward -n sreagent svc/sreagent 8000:80

# Access web interface
# Open http://localhost:8000 in browser
```

## Security Best Practices

1. **Never commit API keys** to version control
2. **Use Kubernetes secrets** for API key storage
3. **Create secrets manually** in production (not via Helm values)
4. **Use RBAC** to restrict secret access
5. **Rotate API keys** regularly
6. **Use separate secrets** for different environments

## Troubleshooting

### Secret Not Found

```bash
# Check if secret exists
kubectl get secret openai-api-key -n sreagent

# If missing, create it
kubectl create secret generic openai-api-key \
  --from-literal=api-key=YOUR_KEY \
  -n sreagent
```

### Model Not Working

1. Check model name is correct:
   ```bash
   kubectl get deployment sreagent -n sreagent -o yaml | grep MODEL
   ```

2. Check API key is set:
   ```bash
   kubectl get deployment sreagent -n sreagent -o yaml | grep OPENAI_API_KEY
   ```

3. Check pod logs for errors:
   ```bash
   kubectl logs -n sreagent deployment/sreagent | grep -i error
   ```

### Switching Models

After changing the model provider, restart the deployment:

```bash
kubectl rollout restart deployment/sreagent -n sreagent
```

## References

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [ADK Models & Authentication](https://google.github.io/adk-docs/agents/models-authentication/)

