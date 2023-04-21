from typing import Optional
from tree_sitter import Node

def find_child_of_type(node, child_type):
    result = None
    for child in node.children:
        if(child.type == child_type):
            result = child
            break
    return result

def find_node_for_range(root_node, start_pos, end_pos) -> Optional[Node]:
    smallest_node: Optional[Node] = None
    smallest_size: Optional[int] = None

    def iterate_nodes(node: Node):
        nonlocal smallest_node, smallest_size
        node_start = node.start_point[0]
        node_end = node.end_point[0]

        if (node_start <= start_pos) and (end_pos <= node_end):
            size = node_end - node_start

            if (smallest_node is None) or (size < smallest_size):
                smallest_node = node
                smallest_size = size

        for child in node.children:
            iterate_nodes(child)

    iterate_nodes(root_node)
    return smallest_node

