---
name: add-data-connection
description: Add an S3 data connection to an existing project
user-invocable: true
allowed-tools:
  - mcp__rhoai__list_data_connections
  - mcp__rhoai__create_s3_data_connection
  - mcp__rhoai__get_data_connection
---

# Add a Data Connection

Add an S3 data connection to an existing project on Red Hat OpenShift AI.

Ask the user for:
- **Namespace**: Target project for the data connection

## Steps

### 1. Check Existing Connections
- Use `mcp__rhoai__list_data_connections` for the namespace
- Verify the connection doesn't already exist

### 2. Gather S3 Credentials
Collect the following from the user:
- **Endpoint URL**: S3 endpoint (e.g., `https://s3.amazonaws.com`)
- **Bucket Name**: The S3 bucket to access
- **Access Key ID**: AWS access key
- **Secret Access Key**: AWS secret key
- **Region**: AWS region (default: `us-east-1`)

### 3. Create the Connection
- Use `mcp__rhoai__create_s3_data_connection` with the gathered credentials
- Choose a meaningful name (e.g., `training-data`, `model-artifacts`)

### 4. Verify the Connection
- Use `mcp__rhoai__get_data_connection` to confirm it was created
- Credentials will be masked in the output

### 5. Usage Notes
- Data connections are automatically available to workbenches
- They can be referenced in model deployments as storage sources
- Training jobs can use them for dataset access

### Security Note
- Credentials are stored as Kubernetes secrets
- Use a dedicated service account with minimal permissions
- Rotate credentials periodically

Provide the S3 connection details to get started.
