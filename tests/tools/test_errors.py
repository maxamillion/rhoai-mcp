"""Tests for enhanced error handling utilities."""


from rhoai_mcp.utils.errors import (
    EnhancedError,
    ErrorPattern,
    enhance_error,
    wrap_error_response,
)


class TestEnhancedError:
    """Test EnhancedError dataclass."""

    def test_create_enhanced_error(self) -> None:
        """Test creating an enhanced error."""
        error = EnhancedError(
            error="Something went wrong",
            error_code="TEST_ERROR",
            suggestion="Try doing X instead",
            related_tools=["tool_a", "tool_b"],
        )

        assert error.error == "Something went wrong"
        assert error.error_code == "TEST_ERROR"
        assert error.suggestion == "Try doing X instead"
        assert error.related_tools == ["tool_a", "tool_b"]

    def test_default_related_tools(self) -> None:
        """Test default empty related tools."""
        error = EnhancedError(
            error="Error",
            error_code="CODE",
            suggestion="Suggestion",
        )

        assert error.related_tools == []

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        error = EnhancedError(
            error="Test error",
            error_code="TEST",
            suggestion="Fix it",
            related_tools=["tool"],
        )

        data = error.to_dict()

        assert data["error"] == "Test error"
        assert data["error_code"] == "TEST"
        assert data["suggestion"] == "Fix it"
        assert data["related_tools"] == ["tool"]


class TestErrorPattern:
    """Test ErrorPattern dataclass."""

    def test_create_pattern(self) -> None:
        """Test creating an error pattern."""
        pattern = ErrorPattern(
            pattern=r"(?i)not found",
            error_code="NOT_FOUND",
            suggestion="Check the resource name",
            related_tools=["list_resources"],
        )

        assert pattern.pattern == r"(?i)not found"
        assert pattern.error_code == "NOT_FOUND"
        assert pattern.suggestion == "Check the resource name"
        assert pattern.related_tools == ["list_resources"]


class TestEnhanceError:
    """Test enhance_error function."""

    def test_enhance_not_found_error(self) -> None:
        """Test enhancing a not found error."""
        enhanced = enhance_error("Resource 'my-workbench' not found in namespace 'test'")

        assert enhanced.error_code == "NOT_FOUND"
        assert "not found" in enhanced.suggestion.lower() or "resource" in enhanced.suggestion.lower()

    def test_enhance_image_pull_error(self) -> None:
        """Test enhancing an ImagePullBackOff error."""
        enhanced = enhance_error("Pod failed: ImagePullBackOff for image jupyter:latest")

        assert enhanced.error_code == "IMAGE_PULL_FAILED"
        assert "image" in enhanced.suggestion.lower()
        assert "list_notebook_images" in enhanced.related_tools

    def test_enhance_gpu_error(self) -> None:
        """Test enhancing a GPU unavailable error."""
        enhanced = enhance_error("Insufficient nvidia.com/gpu resources available")

        assert enhanced.error_code == "GPU_UNAVAILABLE"
        assert "gpu" in enhanced.suggestion.lower()

    def test_enhance_quota_error(self) -> None:
        """Test enhancing a quota exceeded error."""
        enhanced = enhance_error("exceeded quota: cpu request exceeds limit")

        assert enhanced.error_code == "QUOTA_EXCEEDED"
        assert "quota" in enhanced.suggestion.lower() or "resource" in enhanced.suggestion.lower()

    def test_enhance_auth_error(self) -> None:
        """Test enhancing an authentication error."""
        enhanced = enhance_error("Unauthorized: authentication failed for user")

        assert enhanced.error_code == "AUTH_FAILED"
        assert "authentication" in enhanced.suggestion.lower() or "permission" in enhanced.suggestion.lower()

    def test_enhance_namespace_error(self) -> None:
        """Test enhancing a namespace not found error."""
        enhanced = enhance_error("Namespace 'test-project' not found")

        assert enhanced.error_code == "NAMESPACE_NOT_FOUND"
        assert "list_projects" in enhanced.related_tools

    def test_enhance_invalid_name_error(self) -> None:
        """Test enhancing an invalid name error."""
        enhanced = enhance_error("Invalid resource name: must consist of lowercase letters")

        assert enhanced.error_code == "INVALID_NAME"
        assert "dns" in enhanced.suggestion.lower() or "name" in enhanced.suggestion.lower()

    def test_enhance_already_exists_error(self) -> None:
        """Test enhancing an already exists error."""
        enhanced = enhance_error("Resource 'my-workbench' already exists, conflict")

        assert enhanced.error_code == "ALREADY_EXISTS"
        assert "exists" in enhanced.suggestion.lower() or "name" in enhanced.suggestion.lower()

    def test_enhance_unknown_error(self) -> None:
        """Test enhancing an unknown error type."""
        enhanced = enhance_error("Some completely unknown error xyz123")

        assert enhanced.error_code == "UNKNOWN_ERROR"
        assert enhanced.error == "Some completely unknown error xyz123"
        assert enhanced.related_tools == []


class TestWrapErrorResponse:
    """Test wrap_error_response function."""

    def test_wrap_string_error(self) -> None:
        """Test wrapping a string error."""
        response = wrap_error_response("Resource not found")

        assert "error" in response
        assert "error_code" in response
        assert "suggestion" in response
        assert "related_tools" in response

    def test_wrap_exception(self) -> None:
        """Test wrapping an exception."""
        exception = ValueError("Invalid parameter value")
        response = wrap_error_response(exception)

        assert "Invalid parameter value" in response["error"]
        assert response["error_code"]  # Should have some code
        assert response["suggestion"]  # Should have some suggestion

    def test_wrap_preserves_original_message(self) -> None:
        """Test that original message is preserved."""
        original = "The exact error message here"
        response = wrap_error_response(original)

        assert response["error"] == original
