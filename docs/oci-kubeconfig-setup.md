# OCI Kubernetes Configuration for GitHub Actions

## Current OCI Context

**Context Name:** `context-caqincxbd2q`  
**Cluster:** `cluster-caqincxbd2q`  
**Server:** `https://132.226.65.158:6443`  
**Region:** `us-phoenix-1`  
**Cluster OCID:** `ocid1.cluster.oc1.phx.aaaaaaaa3tmb36t4g2yo4nfwnvg3mevafkpminwymx6gibe2ocaqincxbd2q`

## Important Note

The current kubeconfig uses OCI CLI authentication (`oci ce cluster generate-token`), which requires:
- OCI CLI installed
- OCI credentials configured
- Interactive authentication

**This won't work directly in GitHub Actions** because:
1. OCI CLI needs to be installed
2. OCI credentials need to be configured
3. The `exec` plugin requires interactive mode

## Solutions for GitHub Actions

### Option 1: Use OCI Service Account (Recommended)

Create a service account in OCI and use its credentials:

1. **Create OCI Service Account:**
   ```bash
   # In OCI Console or using OCI CLI
   # Create a service account with cluster access
   ```

2. **Generate kubeconfig with service account:**
   ```bash
   oci ce cluster create-kubeconfig \
     --cluster-id ocid1.cluster.oc1.phx.aaaaaaaa3tmb36t4g2yo4nfwnvg3mevafkpminwymx6gibe2ocaqincxbd2q \
     --file ~/.kube/config-oci-service \
     --region us-phoenix-1 \
     --token-version 2.0.0 \
     --kubeconfig-token-provider oci
   ```

3. **Use service account credentials in GitHub Actions:**
   - Add OCI credentials as GitHub secrets:
     - `OCI_TENANCY_OCID`
     - `OCI_USER_OCID`
     - `OCI_FINGERPRINT`
     - `OCI_PRIVATE_KEY` (base64 encoded)
     - `OCI_REGION` (e.g., `us-phoenix-1`)

### Option 2: Use Kubernetes Service Account Token

Create a Kubernetes service account and use its token:

1. **Create service account in OCI cluster:**
   ```bash
   kubectl create serviceaccount github-actions -n sreagent
   kubectl create clusterrolebinding github-actions-binding \
     --clusterrole=cluster-admin \
     --serviceaccount=sreagent:github-actions
   ```

2. **Get the token:**
   ```bash
   SECRET_NAME=$(kubectl get serviceaccount github-actions -n sreagent -o jsonpath='{.secrets[0].name}')
   TOKEN=$(kubectl get secret $SECRET_NAME -n sreagent -o jsonpath='{.data.token}' | base64 -d)
   CA_CERT=$(kubectl get secret $SECRET_NAME -n sreagent -o jsonpath='{.data.ca\.crt}')
   ```

3. **Create kubeconfig:**
   ```yaml
   apiVersion: v1
   kind: Config
   clusters:
   - cluster:
       certificate-authority-data: <CA_CERT>
       server: https://132.226.65.158:6443
     name: cluster-caqincxbd2q
   contexts:
   - context:
       cluster: cluster-caqincxbd2q
       user: github-actions
     name: context-caqincxbd2q
   current-context: context-caqincxbd2q
   users:
   - name: github-actions
     user:
       token: <TOKEN>
   ```

### Option 3: Update GitHub Actions Workflow to Use OCI CLI

Modify the deployment workflow to install and configure OCI CLI:

```yaml
- name: Install OCI CLI
  run: |
    bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)" --accept-all-defaults
    echo "$HOME/bin" >> $GITHUB_PATH

- name: Configure OCI CLI
  env:
    OCI_CLI_USER: ${{ secrets.OCI_USER_OCID }}
    OCI_CLI_TENANCY: ${{ secrets.OCI_TENANCY_OCID }}
    OCI_CLI_FINGERPRINT: ${{ secrets.OCI_FINGERPRINT }}
    OCI_CLI_KEY_CONTENT: ${{ secrets.OCI_PRIVATE_KEY }}
    OCI_CLI_REGION: ${{ secrets.OCI_REGION }}
  run: |
    mkdir -p ~/.oci
    echo "$OCI_CLI_KEY_CONTENT" | base64 -d > ~/.oci/api_key.pem
    chmod 600 ~/.oci/api_key.pem
    oci setup config-file --file ~/.oci/config

- name: Generate kubeconfig
  run: |
    oci ce cluster create-kubeconfig \
      --cluster-id ${{ secrets.OCI_CLUSTER_ID }} \
      --file $HOME/.kube/config \
      --region ${{ secrets.OCI_REGION }} \
      --token-version 2.0.0 \
      --kubeconfig-token-provider oci
```

## Current Kubeconfig (for reference)

The current kubeconfig uses OCI CLI exec plugin. Here's the structure:

```yaml
apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: <BASE64_CA_CERT>
    server: https://132.226.65.158:6443
  name: cluster-caqincxbd2q
contexts:
- context:
    cluster: cluster-caqincxbd2q
    user: user-caqincxbd2q
  name: context-caqincxbd2q
current-context: context-caqincxbd2q
kind: Config
users:
- name: user-caqincxbd2q
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      args:
      - ce
      - cluster
      - generate-token
      - --cluster-id
      - ocid1.cluster.oc1.phx.aaaaaaaa3tmb36t4g2yo4nfwnvg3mevafkpminwymx6gibe2ocaqincxbd2q
      - --region
      - us-phoenix-1
      command: oci
      env: []
      interactiveMode: IfAvailable
      provideClusterInfo: false
```

## Recommended Approach

**Use Option 3** (OCI CLI in GitHub Actions) as it:
- Maintains security with OCI authentication
- Works with existing OCI service accounts
- Provides automatic token refresh
- Is the most secure and maintainable solution

## GitHub Secrets Required

For Option 3, add these secrets:
- `OCI_USER_OCID` - OCI user OCID
- `OCI_TENANCY_OCID` - OCI tenancy OCID
- `OCI_FINGERPRINT` - API key fingerprint
- `OCI_PRIVATE_KEY` - Private key (base64 encoded)
- `OCI_REGION` - Region (e.g., `us-phoenix-1`)
- `OCI_CLUSTER_ID` - Cluster OCID (`ocid1.cluster.oc1.phx.aaaaaaaa3tmb36t4g2yo4nfwnvg3mevafkpminwymx6gibe2ocaqincxbd2q`)

