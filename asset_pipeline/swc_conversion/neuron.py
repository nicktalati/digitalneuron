class Node:
    def __init__(
        self,
        id: int,
        type_id: int,
        x: float,
        y: float,
        z: float,
        r: float,
        parent_id: int
    ):
        self.id = id
        self.type_id = type_id
        self.x, self.y, self.z, self.r = x, y, z, r
        self.parent_id = parent_id
    def __str__(self):
        return f"ID: {self.id}, Parent ID: {self.parent_id}"

class Neuron:
    def __init__(self, swc_filepath: str):
        self.nodes: list[Node] = self.load_nodes(swc_filepath)
        self.root_node = self.get_root(self.nodes)
        node_ids = [n.id for n in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Nodes do not have unique IDs.")

    def load_nodes(self, swc_filepath: str) -> list[Node]:
        nodes: list[Node] = []
        with open(swc_filepath, "r") as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                if line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) != 7:
                    raise ValueError(f"Line does not contain 7 fields: '{line}'")
                node = Node(
                    int(parts[0]),
                    int(parts[1]),
                    float(parts[2]),
                    float(parts[3]),
                    float(parts[4]),
                    float(parts[5]),
                    int(parts[6])
                )
                nodes.append(node)
        return nodes

    def get_children(self, node: Node) -> list[Node]:
        return [n for n in self.nodes if n.parent_id == node.id]

    def get_root(self, nodes: list[Node]) -> Node:
        node_ids = [node.id for node in nodes]
        root_nodes = [node for node in nodes if node.parent_id not in node_ids]
        if len(root_nodes) != 1:
            raise ValueError(f"Root node count != 1; root nodes: {root_nodes}")
        return root_nodes[0]

    def topo_sort(self) -> list[Node]:
        sorted_nodes = [self.root_node]
        seen_ids = {self.root_node.id}

        def add_recurse(node: Node):
            for child_node in self.get_children(node):
                if child_node.id in seen_ids:
                    continue
                seen_ids.add(child_node.id)
                sorted_nodes.append(child_node)
                add_recurse(child_node)

        add_recurse(self.root_node)
        return sorted_nodes
