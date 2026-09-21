"""In-memory model of a repository's file tree as it evolves over commits."""
from __future__ import annotations

from dataclasses import dataclass, field

PULSE_FRAMES = 5  # how many render ticks a touched file stays highlighted
DEATH_FRAMES = 3  # how many render ticks a deleted file stays visible (dying flash)


@dataclass
class Node:
    name: str
    is_dir: bool
    parent: "Node | None" = None
    children: dict = field(default_factory=dict)  # name -> Node
    size: int = 0  # approx line count, for files
    author: str | None = None
    pulse: int = 0
    dying: int = 0

    def full_path(self) -> str:
        parts = []
        node = self
        while node is not None and node.name:
            parts.append(node.name)
            node = node.parent
        return "/".join(reversed(parts))


class FileTree:
    def __init__(self):
        self.root = Node(name="", is_dir=True)
        self._files: dict[str, Node] = {}

    def _get_or_create_dir(self, parts: list[str]) -> Node:
        node = self.root
        for part in parts:
            child = node.children.get(part)
            if child is None:
                child = Node(name=part, is_dir=True, parent=node)
                node.children[part] = child
            node = child
        return node

    def touch(self, path: str, author: str, delta: int, animate: bool = True) -> None:
        """Create/update a file: apply a net line-count delta."""
        parts = path.split("/")
        *dirs, filename = parts
        parent = self._get_or_create_dir(dirs)
        node = parent.children.get(filename)
        if node is None:
            node = Node(name=filename, is_dir=False, parent=parent)
            parent.children[filename] = node
            self._files[path] = node
        node.size = max(0, node.size + delta)
        node.author = author
        node.pulse = PULSE_FRAMES if animate else 0

    def remove(self, path: str, animate: bool = True) -> None:
        node = self._files.get(path)
        if node is None:
            return
        if animate:
            node.dying = DEATH_FRAMES
        else:
            self._files.pop(path, None)
            parent = node.parent
            if parent is not None:
                parent.children.pop(node.name, None)
                self._prune_empty_dirs(parent)

    def sweep_dead(self) -> None:
        """Actually detach nodes whose death animation finished."""
        dead_paths = [p for p, n in self._files.items() if n.dying == 1]
        for path in dead_paths:
            node = self._files.pop(path)
            parent = node.parent
            if parent is not None:
                parent.children.pop(node.name, None)
                self._prune_empty_dirs(parent)

    def _prune_empty_dirs(self, node: Node) -> None:
        while node is not None and node.parent is not None and not node.children:
            parent = node.parent
            parent.children.pop(node.name, None)
            node = parent

    def tick(self) -> None:
        """Advance animation counters by one render frame."""
        for node in list(self._files.values()):
            if node.dying:
                node.dying -= 1
            elif node.pulse:
                node.pulse -= 1
        self.sweep_dead()

    def total_size(self) -> int:
        return sum(n.size for n in self._files.values())

    def file_count(self) -> int:
        return len(self._files)

    def flatten(self) -> list[tuple[int, Node]]:
        """DFS listing of (depth, node), directories sorted before files, both alpha."""
        result: list[tuple[int, Node]] = []

        def walk(node: Node, depth: int):
            dirs = sorted(
                (c for c in node.children.values() if c.is_dir), key=lambda n: n.name
            )
            files = sorted(
                (c for c in node.children.values() if not c.is_dir), key=lambda n: n.name
            )
            for d in dirs:
                result.append((depth, d))
                walk(d, depth + 1)
            for f in files:
                result.append((depth, f))

        walk(self.root, 0)
        return result
