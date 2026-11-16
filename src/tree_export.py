"""Parse tree export: indented text and Graphviz (interfaces.md: tree_export.py).

Depends only on the node classes: it uses `label()` and `children()`.
"""
import shutil

from src.ast_nodes import Node

INDENT = "  "


def tree_to_text(root: Node) -> str:
    """Indented text, one node per line, two spaces per depth level."""
    lines: list[str] = []
    collect_text(root, 0, lines)
    return "\n".join(lines)


def collect_text(node: Node, depth: int, lines: list[str]) -> None:
    """Append this node, then its children one level deeper (pre-order)."""
    lines.append(INDENT * depth + node.label())
    for child in node.children():
        collect_text(child, depth + 1, lines)


def escape_dot(text: str) -> str:
    """Make a label safe inside a double-quoted DOT string."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def tree_to_dot(root: Node) -> str:
    """Graphviz DOT source: one box per node, one edge per parent-child pair."""
    lines = ["digraph ParseTree {", '  node [shape=box, fontname="Helvetica"];']
    collect_dot(root, [0], lines)
    lines.append("}")
    return "\n".join(lines)


def collect_dot(node: Node, counter: list[int], lines: list[str]) -> str:
    """Emit this node and its subtree; return the node's DOT id.

    `counter` is a one-item list used as an id source that is passed down
    explicitly (no global state, rule 12).
    """
    node_id = f"n{counter[0]}"
    counter[0] += 1
    lines.append(f'  {node_id} [label="{escape_dot(node.label())}"];')
    for child in node.children():
        child_id = collect_dot(child, counter, lines)
        lines.append(f"  {node_id} -> {child_id};")
    return node_id


def export_png(root: Node, path: str) -> None:
    """Render the tree to a PNG file with Graphviz.

    Raises RuntimeError with an install hint if the `dot` program is missing,
    so the caller can print one clear message instead of a stack trace.
    """
    if shutil.which("dot") is None:
        raise RuntimeError(
            "Graphviz 'dot' program not found. Install it (macOS: brew install graphviz) "
            "and make sure it is on PATH to use --tree-png.")
    import graphviz   # imported here so the text export works without the package

    try:
        # pipe() returns the PNG bytes without leaving a .gv source file beside the image.
        image = graphviz.Source(tree_to_dot(root)).pipe(format="png")
        with open(path, "wb") as handle:
            handle.write(image)
    except (graphviz.ExecutableNotFound, graphviz.CalledProcessError, OSError) as exc:
        raise RuntimeError(f"Graphviz failed to write '{path}': {exc}") from exc
