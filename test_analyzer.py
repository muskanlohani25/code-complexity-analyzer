"""
test_analyzer.py

Unit tests to verify the C++ Static Complexity Analyzer logic.
Covers comment pre-processing, brace matching, statistics calculations,
complexity estimations, and pattern identification.
"""

import unittest
from helpers import preprocess_cpp_code, find_matching_brace
from analyzer import CPPAnalyzer


class TestHelperFunctions(unittest.TestCase):
    """Tests the comment stripping and brace matching helper routines."""
    
    def test_preprocess_cpp_code_inline_comment(self):
        code = "int a = 5; // inline comment\nint b = 10;"
        res = preprocess_cpp_code(code)
        self.assertNotIn("inline comment", res["stripped_code"])
        self.assertEqual(res["comment_lines_count"], 1)
        self.assertEqual(len(res["stripped_code"].splitlines()), 2)
        
    def test_preprocess_cpp_code_block_comment(self):
        code = "int a = 5;\n/* block comment\nspanning two lines */\nint b = 10;"
        res = preprocess_cpp_code(code)
        self.assertNotIn("block comment", res["stripped_code"])
        self.assertEqual(res["comment_lines_count"], 2)
        self.assertEqual(len(res["stripped_code"].splitlines()), 4)
        
    def test_preprocess_cpp_code_string_with_slashes(self):
        code = 'string url = "http://google.com"; // actual comment'
        res = preprocess_cpp_code(code)
        self.assertIn("http://google.com", res["stripped_code"])
        self.assertNotIn("actual comment", res["stripped_code"])
        self.assertEqual(res["comment_lines_count"], 1)

    def test_find_matching_brace(self):
        code = "void solve() { if(true) { int x = 5; } }"
        # start brace at index 13
        start_idx = code.find('{')
        end_idx = find_matching_brace(code, start_idx)
        self.assertEqual(end_idx, len(code) - 1)


class TestAnalyzerMetrics(unittest.TestCase):
    """Tests statistics collection and complexity estimations."""
    
    def test_stats_procedural_code(self):
        code = """
        // Simple sequential code
        int a = 10;
        int b = 20;
        int sum = a + b;
        if (sum > 20) {
            sum = 0;
        }
        """
        analyzer = CPPAnalyzer(code)
        results = analyzer.get_results()
        
        self.assertEqual(results["time_complexity"], "O(1)")
        self.assertEqual(results["space_complexity"], "O(1)")
        self.assertEqual(results["stats"]["functions_count"], 0)
        self.assertEqual(results["stats"]["if_statements"], 1)
        self.assertEqual(results["stats"]["loops_count"], 0)
        self.assertGreaterEqual(results["stats"]["variables_count"], 3)

    def test_time_complexity_linear_loop(self):
        code = """
        void printN(int n) {
            int sum = 0;
            for (int i = 0; i < n; i++) {
                sum += i;
            }
        }
        """
        analyzer = CPPAnalyzer(code)
        results = analyzer.get_results()
        
        self.assertEqual(results["time_complexity"], "O(n)")
        self.assertEqual(results["space_complexity"], "O(1)")
        self.assertEqual(results["stats"]["loops_count"], 1)
        self.assertEqual(results["stats"]["functions_count"], 1)

    def test_time_complexity_nested_loops(self):
        code = """
        void matrixPrint(int n) {
            for (int i = 0; i < n; i++) {
                for (int j = 0; j < n; j++) {
                    cout << i * j << " ";
                }
            }
        }
        """
        analyzer = CPPAnalyzer(code)
        results = analyzer.get_results()
        
        self.assertEqual(results["time_complexity"], "O(n²)")
        self.assertEqual(results["space_complexity"], "O(1)")
        self.assertEqual(results["stats"]["loops_count"], 2)
        self.assertIn("Nested loops", results["patterns"])

    def test_time_complexity_binary_search(self):
        code = """
        int findIdx(vector<int>& arr, int target) {
            int low = 0, high = arr.size() - 1;
            while (low <= high) {
                int mid = low + (high - low) / 2;
                if (arr[mid] == target) return mid;
                if (arr[mid] < target) low = mid + 1;
                else high = mid - 1;
            }
            return -1;
        }
        """
        analyzer = CPPAnalyzer(code)
        results = analyzer.get_results()
        
        self.assertEqual(results["time_complexity"], "O(log n)")
        self.assertEqual(results["space_complexity"], "O(1)")
        self.assertIn("Binary search", results["patterns"])

    def test_time_complexity_recursive_fibonacci(self):
        code = """
        int fib(int n) {
            if (n <= 1) return n;
            return fib(n - 1) + fib(n - 2);
        }
        """
        analyzer = CPPAnalyzer(code)
        results = analyzer.get_results()
        
        self.assertEqual(results["time_complexity"], "O(2^n)")
        self.assertEqual(results["space_complexity"], "O(n)")
        self.assertIn("Multiple recursion", results["patterns"])
        self.assertIn("Recursion", results["patterns"])

    def test_space_complexity_matrix_declaration(self):
        code = """
        void generateGrid(int n) {
            vector<vector<int>> matrix(n, vector<int>(n, 0));
            matrix[0][0] = 1;
        }
        """
        analyzer = CPPAnalyzer(code)
        results = analyzer.get_results()
        
        self.assertEqual(results["space_complexity"], "O(n²)")
        self.assertEqual(results["time_complexity"], "O(1)")
        self.assertIn("STL usage", results["patterns"])
    def test_cyclomatic_complexity_and_smells(self):
        code = """
        void complexFunc(int x) {
            int y = 99; // Magic number smell
            if (x > 0) {
                if (y > 10) {
                    if (x == y) {
                        for (int i = 0; i < 100; i++) {
                            // Deep Nesting (depth reaches 4)
                        }
                    }
                }
            }
        }
        """
        analyzer = CPPAnalyzer(code)
        results = analyzer.get_results()
        
        # Verify Cyclomatic Complexity
        # Baseline = 1, + 3 ifs + 1 for = 5
        self.assertEqual(results["cyclomatic_complexity"]["overall_value"], 5)
        self.assertEqual(results["cyclomatic_complexity"]["risk_level"], "Low Risk")
        
        # Verify Code Smells
        smell_types = [s["type"] for s in results["code_smells"]]
        self.assertIn("Magic Number", smell_types)
        self.assertIn("Deep Nesting", smell_types)
        
        # Verify Quality Breakdown and Confidence
        self.assertIn("overall", results["quality_scores"])
        self.assertGreaterEqual(results["quality_scores"]["overall"], 0)
        self.assertLessEqual(results["quality_scores"]["overall"], 100)
        self.assertGreaterEqual(results["confidence_score"], 45)


if __name__ == "__main__":
    unittest.main()
