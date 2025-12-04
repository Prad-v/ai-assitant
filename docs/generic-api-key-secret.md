# Generic API Key Secret Configuration

## Overview

The SRE Agent now uses a **single generic secret** (`model-api-key`) that can hold either OpenAI or Gemini API key. This simplifies secret management - you only need to create one secret and can switch between providers by changing the `modelProvider` configuration.

## Configuration

### Helm Values

The generic secret is configured in `values.yaml`:

```yaml
model:
  secretName: "model-api-key"  # Name of the secret
  secretKey: "api-key"         # Key name within the secret
  apiKey: "your-api-key-here"  # API key value (replace with real key)
```

### How It Works

1. **Single Secret**: One secret (`model-api-key`) holds the API key
2. **Provider Selection**: The `app.modelProvider` setting determines which environment variable is populated:
   - If `modelProvider: "openai"` → `OPENAI_API_KEY` is set from the secret
   - If `modelProvider: "gemini"` → `GEMINI_API_KEY` is set from the secret
3. **Flexibility**: You can switch providers by:
   - Changing `app.modelProvider` in values
   - Updating the secret with the appropriate API key

## Creating/Updating the Secret

### Option 1: Via Helm (Development)

The Helm chart will create the secret automatically with a dummy value. Update it with your real key:

```bash
# Update the secret with your OpenAI key
kubectl create secret generic model-api-key \
  --from-literal=api-key=sk-your-openai-key-here \
  --dry-run=client -o yaml | kubectl apply -f - -n sreagent

# Or update the secret with your Gemini key
kubectl create secret generic model-api-key \
  --from-literal=api-key=your-gemini-key-here \
  --dry-run=client -o yaml | kubectl apply -f - -n sreagent
```

### Option 2: Manual Creation

```bash
# Create secret with OpenAI key
kubectl create secret generic model-api-key \
  --from-literal=api-key=sk-your-openai-key-here \
  -n sreagent

# Or create secret with Gemini key
kubectl create secret generic model-api-key \
  --from-literal=api-key=your-gemini-key-here \
  -n sreagent
```

### Option 3: Update Existing Secret

```bash
# Update the secret value
kubectl patch secret model-api-key -n sreagent \
  -p '{"data":{"api-key":"'$(echo -n 'your-new-api-key' | base64)'"}}'
```

## Switching Between Providers

### Switch to OpenAI

1. Update the secret with your OpenAI API key:
   ```bash
   kubectl create secret generic model-api-key \
     --from-literal=api-key=sk-your-openai-key \
     --dry-run=client -o yaml | kubectl apply -f - -n sreagent
   ```

2. Update Helm values:
   ```yaml
   app:
     modelProvider: "openai"
     modelName: "gpt-4-turbo"
   ```

3. Upgrade the release:
   ```bash
   helm upgrade sreagent ./helm/sreagent -n sreagent -f values-dev.yaml
   ```

### Switch to Gemini

1. Update the secret with your Gemini API key:
   ```bash
   kubectl create secret generic model-api-key \
     --from-literal=api-key=your-gemini-key \
     --dry-run=client -o yaml | kubectl apply -f - -n sreagent
   ```

2. Update Helm values:
   ```yaml
   app:
     modelProvider: "gemini"
     modelName: "gemini-2.0-flash"
   ```

3. Upgrade the release:
   ```bash
   helm upgrade sreagent ./helm/sreagent -n sreagent -f values-dev.yaml
   ```

## Verification

### Check Secret Exists

```bash
kubectl get secret model-api-key -n sreagent
```

### Verify Environment Variable in Pod

```bash
# For OpenAI
kubectl exec -n sreagent deployment/sreagent -- env | grep OPENAI_API_KEY

# For Gemini
kubectl exec -n sreagent deployment/sreagent -- env | grep GEMINI_API_KEY
```

### Check Secret Value (Base64 Decoded)

```bash
kubectl get secret model-api-key -n sreagent -o jsonpath='{.data.api-key}' | base64 -d
```

## Migration from Provider-Specific Secrets

If you previously used provider-specific secrets (`openai-api-key` or `gemini-api-key`), you can migrate:

1. **Export the existing secret value**:
   ```bash
   # For OpenAI
   OLD_KEY=$(kubectl get secret openai-api-key -n sreagent -o jsonpath='{.data.api-key}' | base64 -d)
   
   # For Gemini
   OLD_KEY=$(kubectl get secret gemini-api-key -n sreagent -o jsonpath='{.data.api-key}' | base64 -d)
   ```

2. **Create the new generic secret**:
   ```bash
   kubectl create secret generic model-api-key \
     --from-literal=api-key="$OLD_KEY" \
     -n sreagent
   ```

3. **Upgrade Helm release** (this will use the new secret):
   ```bash
   helm upgrade sreagent ./helm/sreagent -n sreagent
   ```

4. **Delete old secrets** (optional):
   ```bash
   kubectl delete secret openai-api-key gemini-api-key -n sreagent
   ```

## Benefits

1. **Simplified Management**: One secret instead of multiple provider-specific secrets
2. **Easy Provider Switching**: Change `modelProvider` and update the secret value
3. **Consistent Configuration**: Same secret structure regardless of provider
4. **Reduced Complexity**: Fewer secrets to manage and rotate

## Security Best Practices

1. **Never commit real API keys** to version control
2. **Use Kubernetes secrets** (not ConfigMaps) for sensitive data
3. **Rotate keys regularly** by updating the secret
4. **Use RBAC** to restrict access to secrets
5. **Consider using external secret management** (e.g., Sealed Secrets, External Secrets Operator) for production

## Troubleshooting

### Secret Not Found

If you see errors about the secret not being found:

```bash
# Verify secret exists
kubectl get secret model-api-key -n sreagent

# If missing, create it
kubectl create secret generic model-api-key \
  --from-literal=api-key=your-key-here \
  -n sreagent
```

### Wrong API Key Being Used

Verify the `modelProvider` setting matches your secret:

```bash
# Check current modelProvider
helm get values sreagent -n sreagent | grep modelProvider

# Check which env var is set in the pod
kubectl exec -n sreagent deployment/sreagent -- env | grep -E "OPENAI_API_KEY|GEMINI_API_KEY"
```

### Secret Update Not Reflected

After updating the secret, restart the pod to pick up the new value:

```bash
kubectl rollout restart deployment/sreagent -n sreagent
```

