import sys
import re
from typing import List, Optional, Tuple
from pathlib import Path
from tree_sitter import Language, Node, Parser

from helpers import treesitter
from helpers import lsp
import pylspclient
from pylspclient.lsp_client import lsp_structs


Language.build_library(
    # Store the library in the `build` directory
    "build/my-languages.so",
    # Include one or more languages
    [
        str(Path(__file__).parent / "vendor/tree-sitter-php"),
    ],
)

PHP_LANGUAGE = Language("build/my-languages.so", "php")

parser = Parser()
parser.set_language(PHP_LANGUAGE)
parsed_files = {}

def parse_file(file_path):
    if(file_path in parsed_files):
        return parsed_files[file_path]
    with file_path.open() as file:
        code = file.read()

    tree = parser.parse(bytes(code, "utf8"))
    root_node = tree.root_node
    parsed_files[file_path] = root_node
    return root_node


class PathObject:
    def __init__(self, file_name, function_name, start_line, match_line_number):
        self.file_name = file_name
        self.function_name = function_name
        self.start_line = start_line
        self.match_line_number = match_line_number

    def __str__(self):
        return f"{self.file_name}: {self.function_name} (line {self.match_line_number})"

    def __repr__(self):
        return self.__str__()


def get_function_or_method_name(node):
    def find_name(child_node):
        if child_node.type == "name":
            return child_node.text

        for grandchild in child_node.children:
            result = find_name(grandchild)
            if result:
                return result.decode()

    if node.type != "method_declaration":
        return None

    return find_name(node)


def find_parent_function_or_method(node):
    while node and node.type not in ["function_definition", "method_declaration"]:
        node = node.parent
    return node


def find_function_or_method(node, name):
    if node.type in ["function_definition", "method_declaration"]:
        function_name = node.child_by_field_name("name")
        if function_name is not None and function_name.text.decode() == name:
            return node

    for child in node.children:
        result = find_function_or_method(child, name)
        if result:
            return result

    return None


def find_function_or_method_by_name(code, name):
    return find_function_or_method(root_node, name)


def collect_function_calls(
    lsp_client,
    node,
    pattern: re.Pattern,
    matches,
    visited_nodes,
    path: List[PathObject],
    file_name: str,
):
    if not (file_name,node) or (file_name,node.id) in visited_nodes:
        return

    visited_nodes.add((file_name, node.id))
    if node.type in ["function_call", "method_declaration"]:
        text = node.text

        function_name = get_function_or_method_name(node)
        function_start_line = node.start_point[0] + 1
        search_results = pattern.finditer(text.decode())
        for search_result in search_results:

            match_start = search_result.start(0)
            # Count the number of newline characters before the match
            lines_before_match = text.decode()[:match_start].count("\n")

            # Calculate the line number of the match in the whole file
            match_line_number = function_start_line + lines_before_match

            path_object = PathObject(
                file_name, function_name, function_start_line, match_line_number
            )
            path.append(path_object)
            matches.append(
                {
                    "node": node,
                    "text": text.decode(),
                    "name": path_object.file_name,
                    "path": path.copy(),
                }
            )

    if node.type in ["member_call_expression", "object_creation_expression"]:
        # Get definition node
        get_definition_result = get_definition_node_of_member_call_expression(
            lsp_client, node, file_name
        )
        if(get_definition_result is None):
            function_name_node = treesitter.find_child_of_type(node, "name")
            print('Could not get definition for', str(function_name_node.text));
        else:
            target_node, target_file_path = get_definition_result

            if target_node:
                collect_function_calls(
                    lsp_client,
                    target_node,
                    pattern,
                    matches,
                    visited_nodes,
                    path,
                    target_file_path,
                )
            else:
                print("No target node for this node")

    for child in node.children:
        collect_function_calls(
            lsp_client, child, pattern, matches, visited_nodes, path, file_name
        )


def get_tree_sitter_node_from_lsp_range(
    lsp_location: pylspclient.lsp_structs.Location,
) -> Tuple[Node, str]:
    target_uri = lsp_location.uri
    target_range = lsp_location.range
    target_file_path = Path(target_uri[7:])  # Remove "file://" from the URI

    root_node = parse_file(target_file_path)
    target_node = treesitter.find_node_for_range(
        root_node, target_range.start.line, target_range.end.line
    )
    if target_node is None:
        #raise Exception("Goto not found")
        return (target_tree.root_node, str(target_file_path))
    else:
        return target_node, str(target_file_path)


def get_path_object_from_node(node, file_name):
    name = get_function_or_method_name(node)
    start_line = node.start_point[0] + 1
    path_object = PathObject(str(file_name), str(name), start_line, start_line)
    return path_object


def get_definition_node_of_member_call_expression(
    lsp_client: lsp.PHP_LSP_CLIENT, node, file_name
)-> Optional[Tuple[Node, str]]:
    if not node or node.type not in [
        "member_call_expression",
        "object_creation_expression",
    ]:
        print("Node is not a member_call_expression")
        return None

    function_name_node = treesitter.find_child_of_type(node, "name")
    start_row, start_col = function_name_node.start_point

    results = lsp_client.get_definitions(file_name, start_row, start_col)

    if not results:
        print(":(  No definition found")
        return None

    tree_nodes = [get_tree_sitter_node_from_lsp_range(result) for result in results]
    tree_nodes = [
        (node, file_name)
        for node, file_name in tree_nodes
        if node.type in ["function_definition", "method_declaration"]
    ]

    if not tree_nodes:
        print("No definition found")
        return None

    return tree_nodes[0]


def search_pattern(lsp_client, file_path, function_name, pattern):

    root_node = parse_file(file_path)
    parent_function = find_function_or_method(root_node, function_name)
    if not parent_function:
        print("Not inside a function or method")
        return

    # Collect matching function calls
    matches = []
    visited_nodes = set()
    path = [get_path_object_from_node(parent_function, str(file_path))]
    collect_function_calls(
        lsp_client,
        parent_function,
        pattern,
        matches,
        visited_nodes,
        path,
        str(file_path),
    )

    # Output the results
    if matches:
        for match in matches:
            match_path_end = match["path"][-1]
            print(
                f"{match_path_end.function_name}: [line {match_path_end.match_line_number}]"
            )
            print("Path:\n", " -> \n ".join(str(p) for p in match["path"]))
            print(match["text"])
    else:
        print("No matches found")


def main():
    if len(sys.argv) < 4:
        print("Usage: python script.py <file> <function> <pattern>")
        sys.exit(1)

    file_path = Path(sys.argv[1])

    if not file_path.is_file():
        print(f"File {file_path} not found")
        sys.exit(1)

    function_name = sys.argv[2]
    pattern = re.compile(sys.argv[3])

    lsp_client = lsp.PHP_LSP_CLIENT()
    search_pattern(lsp_client, file_path, function_name, pattern)

if __name__ == "__main__":
    main()