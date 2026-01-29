"""Tests for tool metadata registry."""

import pytest

from rhoai_mcp.tools.metadata import (
    ToolExample,
    ToolMetadata,
    clear_tool_metadata,
    get_all_tool_metadata,
    get_tool_metadata,
    register_tool_metadata,
)


@pytest.fixture(autouse=True)
def clear_registry() -> None:
    """Clear the metadata registry before each test."""
    clear_tool_metadata()
    yield
    clear_tool_metadata()


class TestToolExample:
    """Test ToolExample dataclass."""

    def test_create_example(self) -> None:
        """Test creating a tool example."""
        example = ToolExample(
            name="basic_usage",
            description="Basic usage of the tool",
            arguments={"arg1": "value1", "arg2": 42},
            expected_result_summary="Returns success status",
            tags=["quick", "basic"],
        )

        assert example.name == "basic_usage"
        assert example.description == "Basic usage of the tool"
        assert example.arguments == {"arg1": "value1", "arg2": 42}
        assert example.expected_result_summary == "Returns success status"
        assert example.tags == ["quick", "basic"]

    def test_default_tags(self) -> None:
        """Test that tags default to empty list."""
        example = ToolExample(
            name="test",
            description="test",
            arguments={},
            expected_result_summary="test",
        )

        assert example.tags == []


class TestToolMetadata:
    """Test ToolMetadata dataclass."""

    def test_create_metadata(self) -> None:
        """Test creating tool metadata."""
        metadata = ToolMetadata(
            name="test_tool",
            display_name="Test Tool",
            description="A tool for testing",
            domain="testing",
        )

        assert metadata.name == "test_tool"
        assert metadata.display_name == "Test Tool"
        assert metadata.description == "A tool for testing"
        assert metadata.domain == "testing"
        assert metadata.examples == []
        assert metadata.prerequisites == []
        assert metadata.related_tools == []
        assert metadata.common_mistakes == []
        assert metadata.error_guidance == {}
        assert metadata.tags == []

    def test_metadata_with_examples(self) -> None:
        """Test metadata with examples."""
        example = ToolExample(
            name="example1",
            description="Example 1",
            arguments={"key": "value"},
            expected_result_summary="Success",
        )

        metadata = ToolMetadata(
            name="test_tool",
            display_name="Test Tool",
            description="A tool for testing",
            domain="testing",
            examples=[example],
            prerequisites=["other_tool"],
            related_tools=["another_tool"],
            common_mistakes=["Common mistake 1"],
            error_guidance={"Error1": "Try X"},
            tags=["read", "quick"],
        )

        assert len(metadata.examples) == 1
        assert metadata.examples[0].name == "example1"
        assert metadata.prerequisites == ["other_tool"]
        assert metadata.related_tools == ["another_tool"]
        assert metadata.common_mistakes == ["Common mistake 1"]
        assert metadata.error_guidance == {"Error1": "Try X"}
        assert metadata.tags == ["read", "quick"]

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        example = ToolExample(
            name="ex1",
            description="Desc",
            arguments={"a": 1},
            expected_result_summary="Result",
            tags=["tag1"],
        )

        metadata = ToolMetadata(
            name="tool1",
            display_name="Tool 1",
            description="Tool description",
            domain="test",
            examples=[example],
            prerequisites=["prereq"],
            tags=["tag"],
        )

        data = metadata.to_dict()

        assert data["name"] == "tool1"
        assert data["display_name"] == "Tool 1"
        assert data["description"] == "Tool description"
        assert data["domain"] == "test"
        assert len(data["examples"]) == 1
        assert data["examples"][0]["name"] == "ex1"
        assert data["prerequisites"] == ["prereq"]
        assert data["tags"] == ["tag"]


class TestMetadataRegistry:
    """Test the metadata registry functions."""

    def test_register_and_get(self) -> None:
        """Test registering and retrieving metadata."""
        metadata = ToolMetadata(
            name="my_tool",
            display_name="My Tool",
            description="My tool description",
            domain="testing",
        )

        register_tool_metadata(metadata)
        retrieved = get_tool_metadata("my_tool")

        assert retrieved is not None
        assert retrieved.name == "my_tool"
        assert retrieved.display_name == "My Tool"

    def test_get_nonexistent(self) -> None:
        """Test getting metadata for unregistered tool."""
        result = get_tool_metadata("nonexistent_tool")

        assert result is None

    def test_get_all_metadata(self) -> None:
        """Test getting all registered metadata."""
        metadata1 = ToolMetadata(
            name="tool1",
            display_name="Tool 1",
            description="Desc 1",
            domain="test",
        )
        metadata2 = ToolMetadata(
            name="tool2",
            display_name="Tool 2",
            description="Desc 2",
            domain="test",
        )

        register_tool_metadata(metadata1)
        register_tool_metadata(metadata2)

        all_metadata = get_all_tool_metadata()

        assert len(all_metadata) == 2
        assert "tool1" in all_metadata
        assert "tool2" in all_metadata

    def test_overwrite_existing(self) -> None:
        """Test that registering overwrites existing metadata."""
        metadata1 = ToolMetadata(
            name="tool",
            display_name="Original",
            description="Original description",
            domain="test",
        )
        metadata2 = ToolMetadata(
            name="tool",
            display_name="Updated",
            description="Updated description",
            domain="test",
        )

        register_tool_metadata(metadata1)
        register_tool_metadata(metadata2)

        retrieved = get_tool_metadata("tool")

        assert retrieved is not None
        assert retrieved.display_name == "Updated"

    def test_clear_metadata(self) -> None:
        """Test clearing all metadata."""
        metadata = ToolMetadata(
            name="tool",
            display_name="Tool",
            description="Desc",
            domain="test",
        )

        register_tool_metadata(metadata)
        assert get_tool_metadata("tool") is not None

        clear_tool_metadata()
        assert get_tool_metadata("tool") is None
        assert len(get_all_tool_metadata()) == 0
