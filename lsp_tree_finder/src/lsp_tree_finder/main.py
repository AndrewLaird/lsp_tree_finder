import sys
import os
import argparse
import re
from typing import List, Optional, Tuple
from pathlib import Path
from tree_sitter import Language, Node, Parser

from lsp_tree_finder.helpers import lsp, treesitter
import pylspclient
from pylspclient.lsp_client import lsp_structs

Language.build_library(
    # Store the library in the `build` directory
    str(Path(__file__).parent / "build/my-languages.so"),
    # Include one or more languages
    [
        str(Path(__file__).parent / "vendor/tree-sitter-php"),
    ],
)

PHP_LANGUAGE = Language(str(Path(__file__).parent / "build/my-languages.so"), "php")

parser = Parser()
parser.set_language(PHP_LANGUAGE)
parsed_files = {}
failed_to_follow = set()


def parse_file(file_path):
    if file_path in parsed_files:
        return parsed_files[file_path]
    with file_path.open() as file:
        code = file.read()

    tree = parser.parse(bytes(code, "utf8"))
    root_node = tree.root_node
    parsed_files[file_path] = root_node
    return root_node


class PathObject:
    def __init__(
        self,
        file_name: str,
        function_name: str,
        start_line: int,
        path_function_call_line: int,
    ):
        self.file_name = file_name
        self.function_name = function_name
        self.start_line = start_line
        self.path_function_call_line = path_function_call_line

    def __str__(self):
        return f"{self.file_name}: {self.function_name} (line {self.path_function_call_line})"

    def __repr__(self):
        return self.__str__()


class MatchObject:
    def __init__(
        self,
        node: treesitter.Node,
        file_name: str,
        function_text: str,
        function_line_number: int,
        match_line_number: int,
        path: List[PathObject],
    ):
        self.node = node
        self.file_name = file_name
        self.function_text = function_text
        self.function_line_number = function_line_number
        self.match_line_number = match_line_number
        self.path = path


def get_function_or_method_name(node) -> str:
    def find_name(child_node):
        if child_node.type == "name":
            return child_node.text

        for grandchild in child_node.children:
            result = find_name(grandchild)
            if result:
                return result.decode()

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


def collect_function_calls(
    lsp_client,
    node,
    pattern: re.Pattern,
    matches,
    visited_nodes,
    path: List[PathObject],
    file_name: str,
    function_node: treesitter.Node,
):
    if not (file_name, node) or (file_name, node.id) in visited_nodes:
        return

    visited_nodes.add((file_name, node.id))
    if node.type in ["function_call", "method_declaration"]:
        text = node.text

        function_start_line = node.start_point[0] + 1
        search_results = pattern.finditer(text.decode())
        for search_result in search_results:

            match_start = search_result.start(0)
            # Count the number of newline characters before the match
            lines_before_match = text.decode()[:match_start].count("\n")

            # Calculate the line number of the match in the whole file
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

    if node.type in ["member_call_expression", "object_creation_expression"]:
        # Get definition node
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

                collect_function_calls(
                    lsp_client,
                    target_node,
                    pattern,
                    matches,
                    visited_nodes,
                    target_path,
                    target_file_path,
                    target_node,
                )
            else:
                print("No target node for this node")

    for child in node.children:
        collect_function_calls(
            lsp_client,
            child,
            pattern,
            matches,
            visited_nodes,
            path,
            file_name,
            function_node,
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
    lsp_client: lsp.PHP_LSP_CLIENT, node, file_name
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

    results = lsp_client.get_definitions(file_name, start_row, start_col)

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
            # for text_line in text_lines:
            # if(line == match_path_end.match_line_number):
            # print(f"***{line} ",text_line)
            # else:
            # print(f"{line} ",text_line)
            #   line += 1
    else:
        print("No matches found")


def search_pattern(lsp_client, file_path, function_name, pattern):
    root_node = parse_file(file_path)
    parent_function = find_function_or_method(root_node, function_name)
    if not parent_function:
        print("Not inside a function or method")
        return

    # Collect matching function calls
    matches = []
    visited_nodes = set()
    path = []
    collect_function_calls(
        lsp_client,
        parent_function,
        pattern,
        matches,
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

    args = parser.parse_args()

    file_path = Path(args.file)

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
