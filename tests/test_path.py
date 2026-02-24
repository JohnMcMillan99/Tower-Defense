import pytest
from map.path_graph import PathGraph
from utils.path_generator import PathGenerator


def test_add_edge():
    """Test adding edges to path graph."""
    graph = PathGraph()

    # Add nodes
    graph.add_node((0, 0))
    graph.add_node((1, 0))

    # Add edge
    graph.add_edge((0, 0), (1, 0))

    # Check edge exists
    assert frozenset({(0, 0), (1, 0)}) in graph.edges


def test_get_ordered_path():
    """Test getting ordered path from start to end."""
    graph = PathGraph()

    # Create a simple path: (0,0) -> (1,0) -> (2,0)
    nodes = [(0, 0), (1, 0), (2, 0)]
    for node in nodes:
        graph.add_node(node)

    graph.add_edge((0, 0), (1, 0))
    graph.add_edge((1, 0), (2, 0))

    # Set start and end
    graph.set_start((0, 0))
    graph.set_end((2, 0))

    path = graph.get_ordered_path()
    assert path == [(0, 0), (1, 0), (2, 0)]


def test_set_start_end():
    """Test setting start and end points."""
    graph = PathGraph()

    start_pos = (0, 0)
    end_pos = (2, 0)

    graph.set_start(start_pos)
    graph.set_end(end_pos)

    # Start and end should be added as nodes
    assert start_pos in graph.nodes
    assert end_pos in graph.nodes

    assert graph.start == start_pos
    assert graph.end == end_pos


def test_path_generator():
    """Test the path generator creates valid paths."""
    generator = PathGenerator(6, 10)

    path = generator.generate_path()

    # Path should not be empty
    assert len(path) > 0

    # All positions should be within bounds
    for x, y in path:
        assert 0 <= x < generator.width
        assert 0 <= y < generator.height

    # Path should be a list of tuples
    assert all(isinstance(pos, tuple) and len(pos) == 2 for pos in path)


def test_path_generator_loop():
    """Test path generator can create loops."""
    generator = PathGenerator(6, 10)

    # Generate initial path
    initial_path = generator.generate_path()
    initial_length = len(initial_path)

    # Try to generate a loop
    loop_added = generator.generate_loop()

    # Loop generation might succeed or fail depending on path structure
    # Either way, the path should still be valid
    assert len(generator.path) >= initial_length

    # All positions should still be within bounds
    for x, y in generator.path:
        assert 0 <= x < generator.width
        assert 0 <= y < generator.height


def test_complex_path():
    """Test building a path graph from generated path."""
    generator = PathGenerator(6, 10)
    generator.generate_path()

    # Build graph from generator path
    graph = PathGraph()

    # Add all path nodes
    for pos in generator.path:
        graph.add_node(pos)

    # Add edges between consecutive nodes
    for i in range(len(generator.path) - 1):
        graph.add_edge(generator.path[i], generator.path[i + 1])

    # Set start and end
    if generator.path:
        graph.set_start(generator.path[0])
        graph.set_end(generator.path[-1])

        # Should be able to get the path back
        ordered_path = graph.get_ordered_path()
        assert ordered_path == generator.path


def test_empty_graph():
    """Test behavior with empty graph."""
    graph = PathGraph()

    # No start/end set
    path = graph.get_ordered_path()
    assert path == []

    # Set start but no end
    graph.set_start((0, 0))
    path = graph.get_ordered_path()
    assert path == []


def test_disconnected_graph():
    """Test behavior with disconnected nodes."""
    graph = PathGraph()

    # Add disconnected nodes
    graph.add_node((0, 0))
    graph.add_node((2, 0))
    graph.set_start((0, 0))
    graph.set_end((2, 0))

    # No path between them
    path = graph.get_ordered_path()
    assert path == []