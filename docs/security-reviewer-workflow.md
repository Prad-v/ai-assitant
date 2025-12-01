# Security Reviewer Workflow Guide

## Overview

The SRE Agent includes a **Security Reviewer (Infosec)** workflow that analyzes Kubernetes resources for security issues, identifies deviations from security best practices, and recommends Kyverno policies to enforce security controls.

## Security Reviewer Capabilities

The agent can act as a security reviewer to:

1. **Analyze Security Issues**: Inspect pods, deployments, statefulsets for security vulnerabilities
2. **Identify Best Practice Deviations**: Compare configurations against Kubernetes security best practices
3. **Recommend Kyverno Policies**: Generate ready-to-apply Kyverno policy YAML for enforcement

## Security Analysis Areas

### 1. Container Security Context

- **Run as Non-Root**: Check for `runAsNonRoot: true` and `runAsUser > 0`
- **Privileged Containers**: Identify containers with `privileged: true`
- **Privilege Escalation**: Check `allowPrivilegeEscalation: false`
- **Read-Only Root Filesystem**: Verify `readOnlyRootFilesystem: true` when possible
- **Capabilities**: Analyze dropped and added capabilities

### 2. Image Security

- **Image Tags**: Identify use of `:latest` tags (insecure)
- **Image Sources**: Verify images from trusted repositories
- **Image Scanning**: Recommend vulnerability scanning

### 3. Resource Management

- **Resource Limits**: Check for missing CPU/memory limits
- **Resource Requests**: Verify resource requests are set
- **Quota Compliance**: Ensure resources fit within quotas

### 4. Secrets Management

- **Secret Mounting**: Verify secrets use `secretKeyRef`, not plain env vars
- **Secret Exposure**: Check for secrets in environment variables
- **Service Account Tokens**: Verify proper service account usage

### 5. Network Security

- **Network Policies**: Check for missing network policies
- **Host Network**: Identify use of `hostNetwork: true`
- **Service Exposure**: Analyze service types and exposure

### 6. Pod Security Standards (PSS)

- **Baseline**: Check compliance with baseline PSS
- **Restricted**: Verify restricted PSS compliance
- **Namespace Policies**: Check for PSS enforcement at namespace level

### 7. RBAC and Access Control

- **Service Accounts**: Verify least privilege service accounts
- **Role Bindings**: Check for excessive permissions
- **Cluster Roles**: Analyze cluster-wide permissions

## Using the Security Reviewer

### Example 1: Review All Deployments

```
User: "Review security of all deployments in default namespace"

Agent will:
1. List all deployments in the namespace
2. Inspect each deployment's security configuration
3. Identify security issues
4. Generate security report
5. Recommend Kyverno policies
```

### Example 2: Analyze Specific Resource

```
User: "Perform security analysis of the test-app deployment"

Agent will:
1. Get deployment spec: kubectl_get deployment test-app -n default
2. Analyze securityContext, containers, volumes
3. Check against security best practices
4. Report findings with severity levels
5. Provide Kyverno policy recommendations
```

### Example 3: Check for Specific Issues

```
User: "Check if any pods are running as root in production namespace"

Agent will:
1. List pods in production namespace
2. Inspect each pod's securityContext
3. Identify root containers
4. Recommend Kyverno policy to enforce non-root
```

## Security Review Report Format

The agent provides structured security reports:

### Executive Summary
- Overall security posture
- Number of critical/high/medium/low findings
- Compliance percentage

### Findings
Each finding includes:
- **Resource**: Name and namespace
- **Issue**: Description of security problem
- **Severity**: Critical, High, Medium, Low
- **Current Configuration**: What's currently set
- **Recommended Configuration**: What should be set
- **Impact**: Potential security impact

### Kyverno Policy Recommendations

For each finding, the agent provides:
- **Policy Name**: Descriptive name
- **Policy Type**: validate, mutate, or generate
- **Enforcement Mode**: enforce or audit
- **Complete YAML**: Ready-to-apply policy

## Common Kyverno Policies

### 1. Require Non-Root Containers

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-non-root
spec:
  validationFailureAction: enforce
  rules:
  - name: require-non-root
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Containers must run as non-root user"
      pattern:
        spec:
          securityContext:
            runAsNonRoot: true
          containers:
          - name: "*"
            securityContext:
              runAsNonRoot: true
```

### 2. Disallow Privileged Containers

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-privileged
spec:
  validationFailureAction: enforce
  rules:
  - name: disallow-privileged
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Privileged containers are not allowed"
      pattern:
        spec:
          containers:
          - name: "*"
            securityContext:
              privileged: false
```

### 3. Require Resource Limits

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
spec:
  validationFailureAction: enforce
  rules:
  - name: require-resource-limits
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Resource limits must be set"
      pattern:
        spec:
          containers:
          - name: "*"
            resources:
              limits:
                memory: "?*"
                cpu: "?*"
```

### 4. Disallow Latest Tag

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-latest-tag
spec:
  validationFailureAction: enforce
  rules:
  - name: disallow-latest-tag
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Image tags must not be 'latest'"
      pattern:
        spec:
          containers:
          - name: "*"
            image: "!*:latest"
```

### 5. Require Read-Only Root Filesystem

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-read-only-rootfs
spec:
  validationFailureAction: enforce
  rules:
  - name: require-read-only-rootfs
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Root filesystem must be read-only"
      pattern:
        spec:
          containers:
          - name: "*"
            securityContext:
              readOnlyRootFilesystem: true
```

## Security Best Practices Checklist

When reviewing resources, the agent checks for:

- [ ] Containers run as non-root (`runAsNonRoot: true`)
- [ ] Privileged containers are disabled (`privileged: false`)
- [ ] Privilege escalation is disabled (`allowPrivilegeEscalation: false`)
- [ ] Read-only root filesystem is enabled (when possible)
- [ ] Resource limits are set for CPU and memory
- [ ] Secrets are mounted via `secretKeyRef`, not env vars
- [ ] Images use specific tags, not `:latest`
- [ ] Network policies are defined
- [ ] Pod Security Standards are enforced
- [ ] Service accounts follow least privilege
- [ ] Host namespaces are not shared
- [ ] Security contexts are defined at pod and container level
- [ ] Capabilities are dropped appropriately
- [ ] No secrets in plain text
- [ ] Proper RBAC permissions

## Example Security Review Session

```
User: "Review security of test-app deployment in default namespace"

Agent Response:
# Security Review Report: test-app Deployment

## Executive Summary
- Overall Security Posture: ⚠️ Needs Improvement
- Critical Findings: 2
- High Findings: 1
- Medium Findings: 3

## Findings

### Critical: Container Running as Root
- **Resource**: test-app deployment, container: test-app
- **Issue**: Container runs as root user (runAsUser not set, runAsNonRoot missing)
- **Severity**: Critical
- **Impact**: Container compromise could lead to host system access
- **Recommendation**: Set runAsNonRoot: true and runAsUser: 1000

### Critical: Missing Resource Limits
- **Resource**: test-app deployment, container: test-app
- **Issue**: No CPU or memory limits defined
- **Severity**: Critical
- **Impact**: Resource exhaustion, potential DoS
- **Recommendation**: Set appropriate resource limits

### High: Privilege Escalation Allowed
- **Resource**: test-app deployment
- **Issue**: allowPrivilegeEscalation not explicitly set to false
- **Severity**: High
- **Impact**: Potential privilege escalation attacks
- **Recommendation**: Set allowPrivilegeEscalation: false

## Recommended Kyverno Policies

### Policy 1: Require Non-Root
[Complete YAML provided]

### Policy 2: Require Resource Limits
[Complete YAML provided]

### Policy 3: Disallow Privilege Escalation
[Complete YAML provided]
```

## Integration with Kyverno

### Installing Kyverno

```bash
# Install Kyverno
kubectl create -f https://github.com/kyverno/kyverno/releases/latest/download/install.yaml

# Verify installation
kubectl get pods -n kyverno
```

### Applying Recommended Policies

1. Review the recommended Kyverno policies from the security review
2. Test policies in `audit` mode first:
   ```yaml
   validationFailureAction: audit
   ```
3. Apply policies:
   ```bash
   kubectl apply -f <policy-name>.yaml
   ```
4. Monitor policy violations:
   ```bash
   kubectl get policyviolations
   ```
5. Switch to `enforce` mode once validated:
   ```yaml
   validationFailureAction: enforce
   ```

## Continuous Security Review

The agent can be used for:

- **Pre-deployment Reviews**: Check resources before deployment
- **Periodic Audits**: Regular security assessments
- **Compliance Checks**: Verify adherence to security standards
- **Policy Validation**: Ensure Kyverno policies are effective

## Best Practices

1. **Start with Audit Mode**: Use `audit` mode for Kyverno policies initially
2. **Gradual Enforcement**: Move to `enforce` mode after validation
3. **Regular Reviews**: Schedule periodic security reviews
4. **Document Findings**: Keep records of security reviews
5. **Track Remediation**: Monitor progress on fixing security issues
6. **Update Policies**: Refine Kyverno policies based on findings

## References

- [Kyverno Documentation](https://kyverno.io/docs/)
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes)

