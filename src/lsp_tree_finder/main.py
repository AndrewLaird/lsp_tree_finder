import sys
import os
import argparse
import re
from typing import List, Optional, Tuple
from pathlib import Path
from tree_sitter import Language, Node, Parser

from lsp_tree_finder.helpers import lsp, treesitter
from lsp_tree_finder.data_classes import PathObject, MatchObject
import pylspclient

PHP_LANGUAGE = Language(str(Path(__file__).parent / "build/my-languages.so"), "php")

parser = Parser()
parser.set_language(PHP_LANGUAGE)
parsed_files = {}
failed_to_follow = set()


def parse_file(file_path) -> Node:
    if file_path in parsed_files:
        return parsed_files[file_path]
    with file_path.open() as file:
        code = file.read()

    tree = parser.parse(bytes(code, "utf8"))
    root_node = tree.root_node
    parsed_files[file_path] = root_node
    return root_node


def get_function_or_method_name(node) -> str:
    def find_name(child_node):
        if child_node.type == "name":
            return child_node.text

        for grandchild in child_node.children:
            result = find_name(grandchild)
            if result:
                return result.decode()
        return ""

    if node.type != "method_declaration":
        return "Not called on a method"

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

def process_function_call_or_declaration(
    node,
    pattern: re.Pattern,
    path: List[PathObject],
    file_name: str,
) -> List[MatchObject]:
    text = node.text
    function_start_line = node.start_point[0] + 1
    matches = []
    search_results = pattern.finditer(text.decode())
    for search_result in search_results:
        match_start = search_result.start(0)
        lines_before_match = text.decode()[:match_start].count("\n")
        match_line_number = function_start_line + lines_before_match
        matches.append(
            MatchObject(
                node=node,
                file_name=os.path.relpath(file_name, os.getcwd()),
                function_text=text.decode(),
                function_line_number=function_start_line,
                match_line_number=match_line_number,
                path=path,
            )
        )
    return matches


def process_member_call_expression_or_object_creation_expression(
    lsp_client,
    node,
    pattern: re.Pattern,
    visited_nodes,
    path: List[PathObject],
    file_name: str,
    function_node: treesitter.Node,
) -> List[MatchObject]:
    matches = []
    get_definition_result = get_definition_node_of_member_call_expression(
        lsp_client, node, file_name
    )
    if get_definition_result is not None:
        target_node, target_file_path = get_definition_result
        if target_node:
            path_object = PathObject(
                file_name=os.path.relpath(file_name, os.getcwd()),
                function_name=get_function_or_method_name(function_node),
                start_line=function_node.start_point[0] + 1,
                path_function_call_line=node.start_point[0] + 1,
            )
            target_path = path.copy()
            target_path.append(path_object)
            matches.extend(
                collect_function_calls(
                    lsp_client,
                    target_node,
                    pattern,
                    visited_nodes,
                    target_path,
                    target_file_path,
                    target_node,
                )
            )
    return matches


def process_children(
    lsp_client,
    node,
    pattern: re.Pattern,
    visited_nodes,
    path: List[PathObject],
    file_name: str,
    function_node: treesitter.Node,
) -> List[MatchObject]:
    matches = []
    for child in node.children:
        matches.extend(
            collect_function_calls(
                lsp_client,
                child,
                pattern,
                visited_nodes,
                path,
                file_name,
                function_node,
            )
        )
    return matches


def collect_function_calls(
    lsp_client,
    node,
    pattern: re.Pattern,
    visited_nodes,
    path: List[PathObject],
    file_name: str,
    function_node: treesitter.Node,
) -> List[MatchObject]:
    if not file_name or not node or (file_name, node.id) in visited_nodes:
        return []
    
    visited_nodes.add((file_name, node.id))
    matches = []

    if node.type in ["function_call", "method_declaration"]:
        matches.extend(
            process_function_call_or_declaration(node, pattern, path, file_name)
        )
    if node.type in ["member_call_expression", "object_creation_expression"]:
        matches.extend(
            process_member_call_expression_or_object_creation_expression(
                lsp_client, node, pattern, visited_nodes, path, file_name, function_node
            )
        )
    matches.extend(process_children(lsp_client, node, pattern, visited_nodes, path, file_name, function_node))

    return matches


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
        # raise Exception("Goto not found")
        return (root_node, str(target_file_path))
    else:
        return target_node, str(target_file_path)


def get_path_object_from_node(node, file_name):
    name = get_function_or_method_name(node)
    start_line = node.start_point[0] + 1
    path_object = PathObject(str(file_name), str(name), start_line, start_line)
    return path_object


def get_definition_node_of_member_call_expression(
        lsp_client: lsp.PHP_LSP_CLIENT, node: Node, file_name: str
) -> Optional[Tuple[Node, str]]:
    if not node or node.type not in [
        "member_call_expression",
        "object_creation_expression",
    ]:
        print("Node is not a member_call_expression")
        return None

    function_name_node = treesitter.find_child_of_type(node, "name")
    if function_name_node is None:
        return None
    start_row, start_col = function_name_node.start_point

    results = lsp_client.get_definitions(file_name, start_row, start_col+1)

    if not results:
        failed_to_follow.add(function_name_node.text.decode())
        return None

    tree_nodes = [get_tree_sitter_node_from_lsp_range(result) for result in results]
    tree_nodes = [
        (node, file_name)
        for node, file_name in tree_nodes
        if node.type in ["function_definition", "method_declaration"]
    ]

    if not tree_nodes:
        return None

    return tree_nodes[0]


def print_matches(matches: List[MatchObject]):
    if matches:
        print("~~~~~~~~~~~~~~~~~")
        print("Failed to follow:")
        print("\n".join([str(p) for p in failed_to_follow]))
        for match in matches:

            print("-----------------")
            print(match.file_name)
            match_text_line = match.match_line_number - match.function_line_number
            text_lines = match.function_text.split("\n")
            print(match.function_line_number, text_lines[0])
            print(match.match_line_number, text_lines[match_text_line])
            print("Path:")
            for path in match.path:
                print(str(path),'->')
            print(match.file_name, text_lines[0])
    else:
        print("No matches found")


def search_pattern(lsp_client, file_path, function_name, pattern) -> List[MatchObject]:
    root_node = parse_file(file_path)
    parent_function = find_function_or_method(root_node, function_name)
    if not parent_function:
        print("Not inside a function or method")
        return []

    visited_nodes = set()
    path = []
    matches = collect_function_calls(
        lsp_client,
        parent_function,
        pattern,
        visited_nodes,
        path,
        str(file_path),
        parent_function,
    )

    return matches


def cli():
    parser = argparse.ArgumentParser(description="Search for a pattern in PHP code.")
    parser.add_argument("file", help="The file to analyze")
    parser.add_argument("function", help="The function to search")
    parser.add_argument("pattern", help="The pattern to search for")
    parser.add_argument("-d", "--directory", help="The working directory")

    args = parser.parse_args()

    file_path = Path(args.file)

    # handling working directory
    if args.directory:
        working_directory = args.directory
    else:
        working_directory = file_path.parent

    os.chdir(working_directory)

    if not file_path.is_file():
        print(f"File {file_path} not found")
        sys.exit(1)

    function_name = args.function
    pattern = re.compile(args.pattern)

    lsp_client = lsp.PHP_LSP_CLIENT()
    matches = search_pattern(lsp_client, file_path, function_name, pattern)
    print_matches(matches)
    lsp_client.close()


if __name__ == "__main__":
    cli()
