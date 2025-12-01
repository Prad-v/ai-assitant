# LiteLLM Model Configuration Guide

## Overview

The SRE Agent uses **LiteLLM** as a standardized interface for all model providers. This provides a unified configuration approach for OpenAI, Gemini, Anthropic, and other supported providers. All API keys are managed through Kubernetes secrets for security.

## Architecture

```
┌─────────────────┐
│  SRE Agent      │
│  (ADK)          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   LiteLLM       │  ← Standardized interface
│   (Unified)      │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│ OpenAI │ │ Gemini │
│  API   │ │  API   │
└────────┘ └────────┘
```

## Model Format

LiteLLM uses a standardized format: `provider/model-name`

Examples:
- `openai/gpt-4-turbo`
- `gemini/gemini-2.0-flash`
- `anthropic/claude-3-opus`

## Configuration

### Helm Values

```yaml
app:
  modelProvider: "gemini"  # or "openai", "anthropic", etc.
  modelName: "gemini-2.0-flash"  # Model name without provider prefix
  maxTokens: null  # Optional: limit response tokens
  temperature: null  # Optional: control randomness (0.0-2.0)

model:
  openai:
    secretName: "openai-api-key"
    secretKey: "api-key"
    apiKey: "sk-dummy-key-replace-with-real-key"  # Only for secret creation
  
  gemini:
    secretName: "gemini-api-key"
    secretKey: "api-key"
    apiKey: "dummy-gemini-key-replace-with-real-key"  # Only for secret creation
```

### Model Selection Logic

The agent automatically formats the model name:
- If `modelName` contains `/` (e.g., `"openai/gpt-4"`), it's used as-is
- Otherwise, it's formatted as `"{modelProvider}/{modelName}"`

## API Key Management

### Creating Secrets

#### For OpenAI

```bash
# Create secret manually (recommended for production)
kubectl create secret generic openai-api-key \
  --from-literal=api-key=YOUR_OPENAI_API_KEY \
  -n sreagent

# Verify
kubectl get secret openai-api-key -n sreagent
```

#### For Gemini

```bash
# Create secret manually (recommended for production)
kubectl create secret generic gemini-api-key \
  --from-literal=api-key=YOUR_GEMINI_API_KEY \
  -n sreagent

# Verify
kubectl get secret gemini-api-key -n sreagent
```

### Secret Structure

The secrets are automatically mounted as environment variables:
- `OPENAI_API_KEY` - for OpenAI models
- `GEMINI_API_KEY` - for Gemini models

## Deployment Examples

### Deploy with Gemini (Default)

```bash
# 1. Create Gemini API key secret
kubectl create secret generic gemini-api-key \
  --from-literal=api-key=YOUR_GEMINI_API_KEY \
  -n sreagent

# 2. Deploy
helm upgrade --install sreagent ./helm/sreagent \
  --namespace sreagent \
  --set app.modelProvider=gemini \
  --set app.modelName=gemini-2.0-flash \
  --set model.gemini.secretName=gemini-api-key
```

### Deploy with OpenAI

```bash
# 1. Create OpenAI API key secret
kubectl create secret generic openai-api-key \
  --from-literal=api-key=YOUR_OPENAI_API_KEY \
  -n sreagent

# 2. Deploy with token optimization
helm upgrade --install sreagent ./helm/sreagent \
  --namespace sreagent \
  --set app.modelProvider=openai \
  --set app.modelName=gpt-4-turbo \
  --set app.maxTokens=2000 \
  --set app.temperature=0.3 \
  --set model.openai.secretName=openai-api-key
```

### Deploy with Custom Model Format

```bash
# Use full model format directly
helm upgrade --install sreagent ./helm/sreagent \
  --namespace sreagent \
  --set app.modelProvider=openai \
  --set app.modelName=openai/gpt-4-turbo-preview \
  --set model.openai.secretName=openai-api-key
```

## Supported Providers

### OpenAI
- `gpt-4`
- `gpt-4-turbo`
- `gpt-4-turbo-preview`
- `gpt-3.5-turbo`
- `gpt-4o`
- `gpt-4o-mini`

### Gemini
- `gemini-2.0-flash`
- `gemini-1.5-pro`
- `gemini-1.5-flash`
- `gemini-pro`

### Anthropic (Claude)
- `claude-3-opus`
- `claude-3-sonnet`
- `claude-3-haiku`

## Environment Variables

The following environment variables are set in the deployment:

- `MODEL_PROVIDER`: Provider name (e.g., "gemini", "openai")
- `MODEL_NAME`: Model name (may include provider prefix)
- `OPENAI_API_KEY`: OpenAI API key (from secret, if provider is openai)
- `GEMINI_API_KEY`: Gemini API key (from secret, if provider is gemini)
- `MAX_TOKENS`: Maximum response tokens (optional)
- `TEMPERATURE`: Temperature setting (optional)

## Verification

### Check Current Configuration

```bash
# Check deployment environment variables
kubectl get deployment sreagent -n sreagent \
  -o jsonpath='{.spec.template.spec.containers[0].env[*]}' | jq

# Check secrets exist
kubectl get secrets -n sreagent | grep -E "(openai|gemini)-api-key"

# Check pod logs for model initialization
kubectl logs -n sreagent deployment/sreagent | grep -i "model\|litellm"
```

### Test the Agent

```bash
# Port forward
kubectl port-forward -n sreagent svc/sreagent 8000:80

# Access web interface
# Open http://localhost:8000/dev-ui/
```

## Switching Models

### Switch from Gemini to OpenAI

```bash
# 1. Create OpenAI secret (if not exists)
kubectl create secret generic openai-api-key \
  --from-literal=api-key=YOUR_OPENAI_API_KEY \
  -n sreagent

# 2. Update deployment
helm upgrade sreagent ./helm/sreagent \
  --namespace sreagent \
  --reuse-values \
  --set app.modelProvider=openai \
  --set app.modelName=gpt-4-turbo \
  --set model.openai.secretName=openai-api-key

# 3. Restart pods
kubectl rollout restart deployment/sreagent -n sreagent
```

### Switch from OpenAI to Gemini

```bash
# 1. Create Gemini secret (if not exists)
kubectl create secret generic gemini-api-key \
  --from-literal=api-key=YOUR_GEMINI_API_KEY \
  -n sreagent

# 2. Update deployment
helm upgrade sreagent ./helm/sreagent \
  --namespace sreagent \
  --reuse-values \
  --set app.modelProvider=gemini \
  --set app.modelName=gemini-2.0-flash \
  --set model.gemini.secretName=gemini-api-key

# 3. Restart pods
kubectl rollout restart deployment/sreagent -n sreagent
```

## Token Optimization

All models support token optimization settings:

```yaml
app:
  maxTokens: 2000  # Limit response tokens
  temperature: 0.3  # Lower = more focused
```

These settings apply to all providers through LiteLLM.

## Troubleshooting

### Model Not Found Error

1. Check model name format:
   ```bash
   kubectl get deployment sreagent -n sreagent -o yaml | grep MODEL_NAME
   ```

2. Verify LiteLLM supports the model:
   - Check [LiteLLM Model List](https://docs.litellm.ai/docs/providers)

### API Key Issues

1. Check secret exists:
   ```bash
   kubectl get secret openai-api-key -n sreagent
   kubectl get secret gemini-api-key -n sreagent
   ```

2. Verify secret is mounted:
   ```bash
   kubectl describe pod -n sreagent -l app.kubernetes.io/name=sreagent | grep -A 5 "Environment:"
   ```

3. Check pod logs:
   ```bash
   kubectl logs -n sreagent deployment/sreagent | grep -i "error\|api.*key"
   ```

### LiteLLM Not Available

If you see "LiteLLM is not available":
1. Check `requirements.txt` includes `litellm>=1.0.0`
2. Rebuild Docker image
3. Verify installation in pod:
   ```bash
   kubectl exec -n sreagent deployment/sreagent -- python -c "import litellm; print(litellm.__version__)"
   ```

## Security Best Practices

1. **Never commit API keys** to version control
2. **Use Kubernetes secrets** for all API keys
3. **Create secrets manually** in production (not via Helm values)
4. **Use RBAC** to restrict secret access
5. **Rotate API keys** regularly
6. **Use separate secrets** for different environments
7. **Use different secrets** for different providers

## Benefits of LiteLLM Standardization

1. **Unified Interface**: Single configuration approach for all providers
2. **Easy Switching**: Change providers without code changes
3. **Consistent API**: Same token optimization settings work for all models
4. **Provider Agnostic**: Add new providers easily
5. **Better Testing**: Test with different providers easily

## References

- [LiteLLM Documentation](https://docs.litellm.ai/)
- [LiteLLM Supported Providers](https://docs.litellm.ai/docs/providers)
- [ADK LiteLLM Integration](https://google.github.io/adk-docs/agents/models/#using-anthropic-models)

