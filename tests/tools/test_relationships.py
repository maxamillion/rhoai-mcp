"""Tests for tool relationships module."""


from rhoai_mcp.tools.relationships import (
    RelationType,
    ToolRelationship,
    Workflow,
    get_all_workflows,
    get_follow_ups,
    get_prerequisites,
    get_tool_relationships,
    get_workflow_for_goal,
)


class TestRelationType:
    """Test RelationType enum."""

    def test_relation_types_exist(self) -> None:
        """Test that all relation types are defined."""
        assert RelationType.PREREQUISITE == "prerequisite"
        assert RelationType.FOLLOW_UP == "follow_up"
        assert RelationType.ALTERNATIVE == "alternative"
        assert RelationType.VALIDATES == "validates"
        assert RelationType.REVERSES == "reverses"


class TestToolRelationship:
    """Test ToolRelationship dataclass."""

    def test_create_relationship(self) -> None:
        """Test creating a tool relationship."""
        rel = ToolRelationship(
            source="tool_a",
            target="tool_b",
            relation=RelationType.PREREQUISITE,
            description="Tool A should be called before Tool B",
        )

        assert rel.source == "tool_a"
        assert rel.target == "tool_b"
        assert rel.relation == RelationType.PREREQUISITE
        assert rel.description == "Tool A should be called before Tool B"


class TestWorkflow:
    """Test Workflow dataclass."""

    def test_create_workflow(self) -> None:
        """Test creating a workflow."""
        wf = Workflow(
            name="my_workflow",
            goal="Achieve something",
            steps=["step1", "step2", "step3"],
            optional_steps=["optional1"],
            tags=["quick", "basic"],
        )

        assert wf.name == "my_workflow"
        assert wf.goal == "Achieve something"
        assert wf.steps == ["step1", "step2", "step3"]
        assert wf.optional_steps == ["optional1"]
        assert wf.tags == ["quick", "basic"]

    def test_default_optional_steps_and_tags(self) -> None:
        """Test default values for optional fields."""
        wf = Workflow(
            name="test",
            goal="Test goal",
            steps=["step1"],
        )

        assert wf.optional_steps == []
        assert wf.tags == []


class TestGetToolRelationships:
    """Test get_tool_relationships function."""

    def test_get_relationships_for_tool(self) -> None:
        """Test getting relationships for a tool that exists in relationships."""
        relationships = get_tool_relationships("create_workbench")

        assert len(relationships) > 0
        # Should include both relationships where create_workbench is source and target
        sources = [r.source for r in relationships]
        targets = [r.target for r in relationships]
        assert "create_workbench" in sources or "create_workbench" in targets

    def test_get_relationships_for_unknown_tool(self) -> None:
        """Test getting relationships for a tool with no defined relationships."""
        relationships = get_tool_relationships("unknown_nonexistent_tool_xyz")

        assert relationships == []


class TestGetPrerequisites:
    """Test get_prerequisites function."""

    def test_get_prerequisites_for_create_workbench(self) -> None:
        """Test getting prerequisites for create_workbench."""
        prerequisites = get_prerequisites("create_workbench")

        # Should include list_notebook_images
        assert "list_notebook_images" in prerequisites

    def test_get_prerequisites_for_tool_without_prereqs(self) -> None:
        """Test getting prerequisites for a tool with none defined."""
        prerequisites = get_prerequisites("list_projects")

        # list_projects is typically a starting point, no prerequisites
        assert isinstance(prerequisites, list)


class TestGetFollowUps:
    """Test get_follow_ups function."""

    def test_get_follow_ups_for_create_workbench(self) -> None:
        """Test getting follow-ups for create_workbench."""
        follow_ups = get_follow_ups("create_workbench")

        # Should include get_workbench and get_workbench_url
        assert "get_workbench" in follow_ups or "get_workbench_url" in follow_ups

    def test_get_follow_ups_for_leaf_tool(self) -> None:
        """Test getting follow-ups for a tool with none defined."""
        follow_ups = get_follow_ups("get_workbench_url")

        # get_workbench_url is typically an endpoint, may have no follow-ups
        assert isinstance(follow_ups, list)


class TestGetWorkflowForGoal:
    """Test get_workflow_for_goal function."""

    def test_find_workbench_workflow(self) -> None:
        """Test finding workflow for workbench creation goal."""
        workflows = get_workflow_for_goal("create workbench")

        assert len(workflows) > 0
        # Should find workbench-related workflow
        names = [wf.name for wf in workflows]
        assert any("workbench" in name for name in names)

    def test_find_gpu_workflow(self) -> None:
        """Test finding workflow for GPU-related goal."""
        workflows = get_workflow_for_goal("gpu training")

        assert len(workflows) > 0

    def test_find_model_deployment_workflow(self) -> None:
        """Test finding workflow for model deployment."""
        workflows = get_workflow_for_goal("deploy model")

        assert len(workflows) > 0

    def test_no_matching_workflow(self) -> None:
        """Test with goal that doesn't match any workflow."""
        workflows = get_workflow_for_goal("xyzzy foobar nonexistent")

        assert workflows == []


class TestGetAllWorkflows:
    """Test get_all_workflows function."""

    def test_get_all_workflows(self) -> None:
        """Test getting all defined workflows."""
        workflows = get_all_workflows()

        assert len(workflows) > 0
        # All items should be Workflow instances
        for wf in workflows:
            assert isinstance(wf, Workflow)
            assert wf.name
            assert wf.goal
            assert len(wf.steps) > 0
