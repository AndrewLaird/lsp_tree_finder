class PathObject:
    def __init__(self, file_name: str, function_name: str, start_line: int, path_function_call_line: int):
        self.file_name = file_name
        self.function_name = function_name
        self.start_line = start_line
        self.path_function_call_line = path_function_call_line

    def __str__(self):
        return f"{self.file_name}: {self.function_name} (line {self.path_function_call_line})"

    def __repr__(self):
        return self.__str__()

class MatchObject:
    def __init__(self, node, file_name: str, function_text: str, function_line_number: int, match_line_number: int, path):
        self.node = node
        self.file_name = file_name
        self.function_text = function_text
        self.function_line_number = function_line_number
        self.match_line_number = match_line_number
        self.path = path
