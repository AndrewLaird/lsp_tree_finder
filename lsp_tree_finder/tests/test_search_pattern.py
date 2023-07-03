import unittest
from pathlib import Path
import re
from lsp_tree_finder.helpers import lsp
from lsp_tree_finder.main import search_pattern, print_matches

class TestSearchPattern(unittest.TestCase):

    def setUp(self):
        self.lsp_client = lsp.PHP_LSP_CLIENT()

    def tearDown(self):
        self.lsp_client.close()

    def test_search_pattern_test1(self):
        file_path = Path("tests/test1.php")
        function_name = "method1"
        pattern = re.compile(r"TestClass2")

        matches = search_pattern(self.lsp_client, file_path, function_name, pattern)
        print(matches)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["path"][-1].file_name, "test1.php")
        self.assertEqual(matches[0]["path"][-1].function_name, "TestClass2")
        self.assertEqual(matches[0]["path"][-1].match_line_number, 9)

    def test_search_pattern_test2(self):
        file_path = Path("tests/test1.php")
        function_name = "method4"
        pattern = re.compile(r"method5")

        matches = search_pattern(self.lsp_client, file_path, function_name, pattern)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["path"][-1].file_name, "test1.php")
        self.assertEqual(matches[0]["path"][-1].function_name, "method5")
        self.assertEqual(matches[0]["path"][-1].match_line_number, 15)

    def test_search_pattern_test3(self):
        file_path = Path("tests/test2.php")
        function_name = "method3"
        pattern = re.compile(r"TestClass1")

        matches = search_pattern(self.lsp_client, file_path, function_name, pattern)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["path"][-1].file_name, "test2.php")
        self.assertEqual(matches[0]["path"][-1].function_name, "TestClass1")
        self.assertEqual(matches[0]["path"][-1].match_line_number, 16)

if __name__ == "__main__":
    unittest.main()
