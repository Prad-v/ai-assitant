# Cluster Inventory Management

## Overview

The Cluster Inventory feature allows administrators to manage multiple Kubernetes clusters by uploading and storing kubeconfig files. This enables the SRE Agent to work with multiple clusters and switch between them during troubleshooting sessions.

## Features

- **Upload Kubeconfig**: Upload kubeconfig files for multiple Kubernetes clusters
- **Auto-Discovery**: Automatically discover and register the in-cluster configuration when running inside Kubernetes
- **Cluster List**: View all registered clusters with their status and metadata
- **Connection Testing**: Test cluster connectivity before using it
- **Cluster Selection**: Select which cluster to use in chat sessions
- **Secure Storage**: Kubeconfigs are stored as Kubernetes Secrets (encrypted at rest)
- **Metadata Management**: Store cluster names, descriptions, and tags

## Architecture

### Storage

- **Kubeconfig Files**: Stored as Kubernetes Secrets with prefix `cluster-kubeconfig-{cluster-id}`
- **Cluster Metadata**: Stored in a ConfigMap named `cluster-inventory`
- **Benefits**: 
  - Leverages Kubernetes native security (encryption at rest)
  - No external database dependencies
  - Integrated with Kubernetes RBAC

### API Endpoints

The backend provides the following REST API endpoints:

- `POST /clusters` - Register a new cluster
- `GET /clusters` - List all clusters
- `GET /clusters/{id}` - Get cluster details
- `PUT /clusters/{id}` - Update cluster information
- `DELETE /clusters/{id}` - Delete a cluster
- `POST /clusters/{id}/test` - Test cluster connection
- `GET /clusters/{id}/info` - Get detailed cluster information
- `POST /clusters/discover` - Manually trigger in-cluster discovery

### Frontend

- **Inventory Page**: `/inventory` - Main page for managing clusters
- **Cluster Selector**: Dropdown in chat interface to select active cluster
- **Upload Modal**: Form for adding new clusters
- **Details Modal**: View cluster information and test connections

## Usage

### Auto-Discovery

When the SRE Agent is running inside a Kubernetes cluster, it automatically:
- Detects that it's running in-cluster
- Generates a kubeconfig from the service account token and CA certificate
- Registers the cluster in the inventory with tags `["auto-discovered", "in-cluster"]`
- Uses a friendly name based on the cluster's API server hostname and namespace

The auto-discovery happens on startup. If you need to manually trigger it, use the API endpoint:
```bash
curl -X POST http://localhost:8000/api/clusters/discover
```

### Adding a Cluster Manually

1. Navigate to the **Cluster Inventory** page from the main navigation
2. Click **+ Add Cluster**
3. Fill in the form:
   - **Cluster Name**: Display name for the cluster
   - **Description**: Optional description
   - **Tags**: Comma-separated tags (e.g., "production, us-east")
   - **Kubeconfig**: Upload a file or paste the kubeconfig content
4. Click **Add Cluster**

The system will:
- Validate the kubeconfig format
- Store the kubeconfig as a Kubernetes Secret
- Store metadata in a ConfigMap
- Optionally test the connection

### Using a Cluster in Chat

1. In the chat interface, use the **Cluster** dropdown at the top
2. Select the desired cluster
3. The agent will use the selected cluster's kubeconfig for all operations
4. If no cluster is selected, the agent uses the default cluster context

### Testing Cluster Connection

1. Go to the **Cluster Inventory** page
2. Click on a cluster card to view details
3. Click **Test Connection** to verify connectivity
4. The status will update based on the test result

### Deleting a Cluster

1. Go to the **Cluster Inventory** page
2. Click the **Delete** button on a cluster card
3. Confirm the deletion
4. Both the kubeconfig Secret and metadata will be removed

## RBAC Requirements

The SRE Agent service account needs the following permissions:

```yaml
rules:
  # Cluster inventory management
  - apiGroups: [""]
    resources: ["secrets"]
    resourceNames: ["cluster-kubeconfig-*"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  - apiGroups: [""]
    resources: ["configmaps"]
    resourceNames: ["cluster-inventory"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```

These permissions are automatically configured in the Helm chart's `rbac.yaml`.

## Security Considerations

1. **Kubeconfig Storage**: Kubeconfigs are stored as Kubernetes Secrets, which are encrypted at rest (if encryption is enabled in your cluster)
2. **Access Control**: Only users with access to the SRE Agent namespace can manage clusters
3. **Validation**: Kubeconfigs are validated before storage to prevent invalid configurations
4. **Connection Testing**: Clusters are tested before use to ensure connectivity

## Troubleshooting

### Cluster Connection Test Fails

- Verify the kubeconfig is valid and not expired
- Check network connectivity to the cluster
- Ensure the cluster API server is accessible
- Verify RBAC permissions for the kubeconfig user

### Cluster Not Appearing in List

- Check backend logs for errors
- Verify the service account has necessary RBAC permissions
- Check if Secrets and ConfigMaps are being created in the namespace

### Cannot Delete Cluster

- Verify RBAC permissions for deleting Secrets and ConfigMaps
- Check if the cluster is currently in use (may need to deselect it first)

## Future Enhancements

- Cluster grouping and organization
- Automatic cluster discovery
- Cluster health monitoring
- Multi-cluster queries (query all clusters at once)
- Cluster usage analytics
- Kubeconfig rotation and expiration management

