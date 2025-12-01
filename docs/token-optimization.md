# Token Optimization Guide

## Overview

This guide explains how to optimize token usage when using the SRE Agent with MCP tools, especially when using OpenAI models that have rate limits.

## Token Optimization Strategies

### 1. Use Efficient Models

**For OpenAI:**
- Use `gpt-4-turbo` instead of `gpt-4` for better rate limits and lower cost
- Configure in `helm/sreagent/values.yaml`:
  ```yaml
  app:
    modelProvider: "openai"
    modelName: "gpt-4-turbo"  # More efficient than gpt-4
  ```

**For Gemini:**
- Use `gemini-2.0-flash` for fast, efficient responses
- Configure in `helm/sreagent/values.yaml`:
  ```yaml
  app:
    modelProvider: "gemini"
    modelName: "gemini-2.0-flash"
  ```

### 2. Configure Token Limits

You can limit the maximum tokens in responses to reduce token consumption:

```yaml
app:
  maxTokens: 2000  # Limit response tokens (null = no limit)
  temperature: 0.3  # Lower temperature = more focused responses (0.0-2.0, null = default)
```

**Example Deployment:**
```bash
helm upgrade sreagent ./helm/sreagent \
  --namespace sreagent \
  --set app.maxTokens=2000 \
  --set app.temperature=0.3
```

### 3. Optimized Agent Instructions

The agent has been configured with token-efficient instructions that:
- Encourage specific queries instead of listing all resources
- Limit log retrieval to last 50-100 lines
- Use field selectors for targeted queries
- Avoid redundant queries by caching information

### 4. Best Practices for Queries

When interacting with the agent, follow these practices:

**✅ Good (Token Efficient):**
- "Check the status of pod test-app-xyz in default namespace"
- "Get the last 50 lines of logs for pod test-app-xyz"
- "List events for pod test-app-xyz with fieldSelector"

**❌ Avoid (Token Heavy):**
- "List all pods in all namespaces"
- "Get all logs for all pods"
- "Show me everything about the cluster"

### 5. Monitor Token Usage

To monitor token usage and identify optimization opportunities:

1. **Check OpenAI Dashboard:**
   - Visit https://platform.openai.com/usage
   - Monitor token consumption per request
   - Track rate limit usage

2. **Review Agent Logs:**
   ```bash
   kubectl logs -n sreagent -l app.kubernetes.io/name=sreagent --tail=100
   ```

3. **Watch for Rate Limit Errors:**
   - If you see `RateLimitError`, consider:
     - Switching to `gpt-4-turbo` or `gemini-2.0-flash`
     - Reducing `maxTokens`
     - Lowering `temperature` for more focused responses

## Configuration Examples

### Minimal Token Usage (OpenAI)
```yaml
app:
  modelProvider: "openai"
  modelName: "gpt-4-turbo"
  maxTokens: 1500
  temperature: 0.2
```

### Balanced (Gemini - Recommended)
```yaml
app:
  modelProvider: "gemini"
  modelName: "gemini-2.0-flash"
  # maxTokens and temperature not needed for Gemini
```

### High Performance (OpenAI)
```yaml
app:
  modelProvider: "openai"
  modelName: "gpt-4-turbo"
  maxTokens: 3000
  temperature: 0.5
```

## Troubleshooting

### Rate Limit Errors

If you encounter rate limit errors:

1. **Switch to Gemini:**
   ```bash
   helm upgrade sreagent ./helm/sreagent \
     --namespace sreagent \
     --set app.modelProvider=gemini \
     --set app.modelName=gemini-2.0-flash
   ```

2. **Reduce Token Usage:**
   ```bash
   helm upgrade sreagent ./helm/sreagent \
     --namespace sreagent \
     --set app.maxTokens=1000 \
     --set app.temperature=0.1
   ```

3. **Upgrade OpenAI Plan:**
   - Visit https://platform.openai.com/account/billing
   - Upgrade to a plan with higher rate limits

### Verify Configuration

Check that token optimization settings are applied:

```bash
# Check environment variables
kubectl get pod -n sreagent -l app.kubernetes.io/name=sreagent \
  -o jsonpath='{.items[0].spec.containers[0].env}' | jq

# Check logs for model configuration
kubectl logs -n sreagent -l app.kubernetes.io/name=sreagent | grep -i model
```

## Expected Token Savings

With these optimizations, you can expect:
- **40-60% reduction** in token usage for MCP queries
- **Faster responses** due to more focused queries
- **Lower costs** when using OpenAI models
- **Better rate limit compliance** with OpenAI API

## Additional Resources

- [OpenAI Rate Limits](https://platform.openai.com/docs/guides/rate-limits)
- [ADK Documentation](https://google.github.io/adk-docs/)
- [LiteLLM Documentation](https://docs.litellm.ai/)

