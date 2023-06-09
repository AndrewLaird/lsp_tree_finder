import unittest
import os
from pathlib import Path
import re
from lsp_tree_finder.helpers import lsp
from lsp_tree_finder.main import search_pattern

class TestSearchPattern(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(__file__).parent / "example_directory";
        self.lsp_client = lsp.PHP_LSP_CLIENT()
        os.chdir(Path(__file__).parent / "example_directory")

    def tearDown(self):
        self.lsp_client.close()

    def test_search_pattern_test1(self):
        file_path = self.test_dir / "test1.php"
        function_name = "method1"
        pattern = re.compile(r"TestClass2")

        matches = search_pattern(self.lsp_client, file_path, function_name, pattern)
        self.assertEqual(len(matches), 2)
        self.assertEqual(Path(matches[0].file_name).name, "test1.php")
        self.assertEqual(Path(matches[1].file_name).name, "test2.php")
        self.assertEqual(matches[0].match_line_number, 11)
        self.assertEqual(matches[1].match_line_number, 7)

    def test_search_pattern_test2(self):
        file_path = self.test_dir / "test1.php"
        function_name = "method4"
        pattern = re.compile(r"method4\(\);")

        matches = search_pattern(self.lsp_client, file_path, function_name, pattern)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].file_name, "test1.php")
        self.assertEqual(matches[0].match_line_number, 21)

    def test_search_pattern_test3(self):
        file_path = self.test_dir / "test2.php"
        function_name = "method3"
        pattern = re.compile(r" TestClass1\.")

        matches = search_pattern(self.lsp_client, file_path, function_name, pattern)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].file_name, "test1.php")
        self.assertEqual(matches[0].match_line_number, 26)

if __name__ == "__main__":
    unittest.main()
