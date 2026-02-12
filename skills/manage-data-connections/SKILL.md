---
name: manage-data-connections
description: Create and manage S3 data connections in RHOAI projects. Use when the user needs to configure access to S3-compatible storage for models or datasets.
license: Apache-2.0
compatibility: Requires oc or kubectl and jq. Needs an OpenShift cluster with RHOAI installed.
metadata:
  author: Red Hat
  version: "1.0"
  category: management
---

# Manage Data Connections

Create and manage S3-compatible data connections in Red Hat OpenShift AI (RHOAI)
projects. Data connections are Kubernetes secrets that store S3 credentials and
endpoint information, used by workbenches, pipelines, and model serving to access
object storage.

## Prerequisites

- `oc` or `kubectl` CLI installed and authenticated to the cluster
- `jq` installed for JSON processing
- An OpenShift cluster with Red Hat OpenShift AI (RHOAI) installed
- A target Data Science Project (namespace) must already exist

## Workflow

### Step 1: Check cluster authentication

Verify that you are authenticated to the cluster and that RHOAI is installed.

```bash
bash ../_shared/auth-check.sh
```

If authentication fails, run `oc login` with the appropriate cluster URL and
credentials before continuing.

### Step 2: List existing connections

Check what data connections already exist in the target project.

```bash
bash scripts/list-connections.sh NAMESPACE
```

Replace `NAMESPACE` with the Data Science Project name. This outputs a JSON
array of existing S3 data connections including their names, endpoints, buckets,
and regions. Secret access keys are masked in the output for security.

### Step 3: Create a new data connection

Create a new S3 data connection with the required credentials.

```bash
bash scripts/create-s3-connection.sh NAMESPACE NAME ENDPOINT BUCKET ACCESS_KEY SECRET_KEY [--region REGION] [--display-name "Display Name"]
```

Required parameters:
- `NAMESPACE` -- the target Data Science Project
- `NAME` -- name for the Kubernetes secret (must be DNS-compatible)
- `ENDPOINT` -- S3-compatible endpoint URL (e.g., `https://s3.amazonaws.com`)
- `BUCKET` -- S3 bucket name
- `ACCESS_KEY` -- AWS/S3 access key ID
- `SECRET_KEY` -- AWS/S3 secret access key

Optional parameters:
- `--region REGION` -- AWS region (defaults to `us-east-1`)
- `--display-name "Display Name"` -- human-readable name shown in the RHOAI dashboard

## Required information

To create a data connection, you need the following from the user:
- **S3 endpoint**: The URL of the S3-compatible object storage service
- **Bucket name**: The name of the S3 bucket to connect to
- **Access key**: The access key ID for authentication
- **Secret key**: The secret access key for authentication
- **Region**: The AWS region (optional, defaults to `us-east-1`)

## Notes

- Data connections appear in the RHOAI dashboard under the project's
  "Data connections" tab.
- The secret access key is stored as a Kubernetes secret and is base64 encoded.
  It is never displayed in plain text in script output.
- Multiple data connections can exist in a single project, each pointing to
  different buckets or storage services.
- Data connections can be referenced by workbenches, pipeline components, and
  model serving configurations.
- To delete a data connection, delete the corresponding Kubernetes secret from
  the namespace.
