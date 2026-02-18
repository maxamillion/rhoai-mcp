"""MCP Tools for Data Connection operations.

Note: list_data_connections and get_data_connection have been consolidated
into the cluster composite tools (list_resources, get_resource).
"""

from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

from rhoai_mcp.domains.connections.client import ConnectionClient
from rhoai_mcp.domains.connections.models import S3DataConnectionCreate

if TYPE_CHECKING:
    from rhoai_mcp.server import RHOAIServer


def register_tools(mcp: FastMCP, server: "RHOAIServer") -> None:
    """Register data connection tools with the MCP server."""

    @mcp.tool()
    def create_s3_data_connection(
        name: str,
        namespace: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_s3_endpoint: str,
        aws_s3_bucket: str,
        display_name: str | None = None,
        aws_default_region: str = "us-east-1",
    ) -> dict[str, Any]:
        """Create an S3 data connection.

        Creates a secret with the appropriate RHOAI labels and annotations
        that can be used by workbenches and pipelines to access S3 storage.

        Args:
            name: Connection name (will be the secret name).
            namespace: Project (namespace) name.
            aws_access_key_id: AWS Access Key ID.
            aws_secret_access_key: AWS Secret Access Key.
            aws_s3_endpoint: S3 endpoint URL (e.g., https://s3.amazonaws.com).
            aws_s3_bucket: S3 bucket name.
            display_name: Human-readable display name.
            aws_default_region: AWS region (default: us-east-1).

        Returns:
            Created data connection information (credentials masked).
        """
        # Check if operation is allowed
        allowed, reason = server.config.is_operation_allowed("create")
        if not allowed:
            return {"error": reason}

        client = ConnectionClient(server.k8s)
        request = S3DataConnectionCreate(
            name=name,
            namespace=namespace,
            display_name=display_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_s3_endpoint=aws_s3_endpoint,
            aws_s3_bucket=aws_s3_bucket,
            aws_default_region=aws_default_region,
        )
        conn = client.create_s3_data_connection(request)

        return {
            "name": conn.metadata.name,
            "namespace": conn.metadata.namespace,
            "type": conn.connection_type,
            "bucket": conn.aws_s3_bucket,
            "message": f"Data connection '{name}' created successfully",
            "_source": conn.metadata.to_source_dict(),
        }

    @mcp.tool()
    def delete_data_connection(
        name: str,
        namespace: str,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Delete a data connection.

        WARNING: Workbenches or pipelines using this connection will lose
        access to the associated data source.

        Args:
            name: The data connection (secret) name.
            namespace: The project (namespace) name.
            confirm: Must be True to actually delete.

        Returns:
            Confirmation of deletion.
        """
        # Check if operation is allowed
        allowed, reason = server.config.is_operation_allowed("delete")
        if not allowed:
            return {"error": reason}

        if not confirm:
            return {
                "error": "Deletion not confirmed",
                "message": (
                    f"To delete data connection '{name}', set confirm=True. "
                    "WARNING: Resources using this connection will lose access."
                ),
            }

        client = ConnectionClient(server.k8s)
        client.delete_data_connection(name, namespace)

        return {
            "name": name,
            "namespace": namespace,
            "deleted": True,
            "message": f"Data connection '{name}' deleted",
            "_source": {
                "kind": "Secret",
                "api_version": "v1",
                "name": name,
                "namespace": namespace,
                "uid": None,
            },
        }
