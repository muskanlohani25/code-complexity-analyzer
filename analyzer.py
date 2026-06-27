"""
analyzer.py

This module contains the core static analysis engine for C++ code.
It parses code structure (without compilation) to estimate time and space complexities,
compute code statistics, detect patterns, and suggest optimizations.
"""

import re
from helpers import preprocess_cpp_code, find_matching_brace

class CPPAnalyzer:
    """
    Core static analyzer class for C++ code.
    Processes the raw code string, extracts statistics, parses functions,
    estimates complexities, detects patterns, and provides optimization tips.
    """
    
    def __init__(self, raw_code: str):
        self.raw_code = raw_code
        # Preprocess code to strip comments while keeping line structure
        prep_results = preprocess_cpp_code(raw_code)
        self.code = prep_results["stripped_code"]
        self.comment_lines_count = prep_results["comment_lines_count"]
        
        # Split preprocessed code into lines
        self.lines = self.code.splitlines()
        self.total_lines = len(self.raw_code.splitlines())
        
        # Basic counts
        self.blank_lines = sum(1 for line in self.lines if not line.strip())
        
        # Main results placeholder
        self.functions = []
        self.global_stats = {}
        self.patterns = []
        self.suggestions = []
        self.complexity_explanation = []
        
        # Analyze
        self._analyze()

    def _analyze(self):
        """
        Executes the static analysis pipeline:
        1. Extract function blocks.
        2. Analyze each function (loops, recursion, variables, if-statements).
        3. Estimate complexities.
        4. Detect patterns.
        5. Generate suggestions.
        """
        # 1. Extract functions
        self.functions = self._extract_functions()
        
        # 2. Extract stats across functions or the whole code
        self.global_stats = self._compute_statistics()
        
        # 3. Estimate complexities & generate explanations
        time_comp, space_comp = self._estimate_complexities()
        self.time_complexity = time_comp
        self.space_complexity = space_comp
        
        # 4. Detect patterns
        self._detect_patterns()
        
        # 5. Generate optimizations
        self._generate_suggestions()

        # 6. Calculate Cyclomatic Complexity
        self.cyclomatic_complexity = self._calculate_cyclomatic_complexity()

        # 7. Detect Code Smells
        self.code_smells = self._detect_code_smells()

        # 8. Calculate Code Quality Scores
        self.quality_scores = self._calculate_code_quality_scores()

        # 9. Estimate Complexity Confidence Score
        self.confidence_score = self._calculate_confidence_score()


    def _extract_functions(self) -> list:
        """
        Parses C++ code to locate function definitions at top level (brace depth 0).
        
        Returns:
            list: List of dicts representing function name, body, return type, bounds.
        """
        functions = []
        n = len(self.code)
        i = 0
        in_string = False
        in_char = False
        escape = False
        brace_depth = 0
        last_block_end = 0

        while i < n:
            c = self.code[i]
            next_c = self.code[i+1] if i + 1 < n else ''

            if in_string:
                if escape:
                    escape = False
                elif c == '\\':
                    escape = True
                elif c == '"':
                    in_string = False
                i += 1
                continue
            elif in_char:
                if escape:
                    escape = False
                elif c == '\\':
                    escape = True
                elif c == "'":
                    in_char = False
                i += 1
                continue

            if c == '"':
                in_string = True
                i += 1
            elif c == "'":
                in_char = True
                i += 1
            elif c == '{':
                if brace_depth == 0:
                    # Capture header from last_block_end to current '{'
                    header = self.code[last_block_end:i].strip()
                    end_brace = find_matching_brace(self.code, i)
                    
                    if end_brace != -1:
                        func_info = self._parse_function_header(header)
                        if func_info:
                            func_info['start_idx'] = i
                            func_info['end_idx'] = end_brace
                            func_info['body'] = self.code[i+1:end_brace]
                            functions.append(func_info)
                        
                        # Skip past the entire brace block
                        i = end_brace + 1
                        last_block_end = i
                        continue
                brace_depth += 1
                i += 1
            elif c == '}':
                brace_depth = max(0, brace_depth - 1)
                i += 1
            elif c == ';':
                if brace_depth == 0:
                    last_block_end = i + 1
                i += 1
            else:
                i += 1

        return functions

    def _parse_function_header(self, header: str) -> dict:
        """
        Analyzes header string of a block to see if it is a C++ function.
        Excludes control keywords like for, while, if, struct, class.

        Args:
            header (str): The signature prefix before a block opens.

        Returns:
            dict or None: Dict of return_type, name, parameters, or None if invalid.
        """
        # Clean header whitespace
        header = re.sub(r'\s+', ' ', header).strip()
        
        # Exclude common control statements and class/struct declarations
        exclude_keywords = (
            'if', 'for', 'while', 'switch', 'catch', 'else', 
            'class', 'struct', 'namespace', 'union', 'enum'
        )
        if any(header.startswith(kw) or re.search(r'\b' + kw + r'\b', header) for kw in exclude_keywords):
            return None
            
        # Must contain parameters parenthesis
        if '(' not in header or ')' not in header:
            return None
            
        # Standard function declaration pattern: ReturnType Name(Params...)
        # We find the name preceding the first '('
        paren_idx = header.find('(')
        pre_paren = header[:paren_idx].strip()
        
        # Split tokens to find name and return type
        tokens = pre_paren.split()
        if not tokens:
            return None
            
        name = tokens[-1]
        
        # Handle cases where name is an operator or template syntax
        # Basic identifier validation (allow standard alphanumeric name)
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
            # Check for constructor or class member function e.g. Solution::solve
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*::[a-zA-Z_][a-zA-Z0-9_]*$', name):
                return None
            
        return_type = " ".join(tokens[:-1])
        
        # Extract params
        params_str = header[paren_idx + 1:header.find(')', paren_idx)]
        
        return {
            "name": name,
            "return_type": return_type if return_type else "void",
            "params": params_str
        }

    def _compute_statistics(self) -> dict:
        """
        Computes various statistics of the C++ code such as lines, functions,
        loops, recursive calls, if statements, and variables.
        """
        # Count if statements: match "if" keyword (not preceded by alphanumeric)
        # Avoid matching variables containing "if" e.g., "gift"
        if_count = len(re.findall(r'\bif\b\s*\(', self.code))
        
        # Count loops: for, while, do-while
        for_count = len(re.findall(r'\bfor\b\s*\(', self.code))
        # while count, avoiding "do { ... } while (...);" double count if possible
        # But statically we can count "\bwhile\b" and then subtract do-while
        do_while_count = len(re.findall(r'\bdo\b\s*\{', self.code))
        raw_while_count = len(re.findall(r'\bwhile\b\s*\(', self.code))
        while_count = max(0, raw_while_count - do_while_count)
        total_loops = for_count + while_count + do_while_count
        
        # Variables count
        # Simple C++ variable declaration parser
        # Matches common types followed by comma separated list of variables ending with semicolon
        # int a = 5, b; or vector<int> vec;
        var_types = r'\b(int|double|float|char|string|bool|long|short|unsigned|auto|vector|std::vector|map|std::map|unordered_map|std::unordered_map|set|std::set|unordered_set|std::unordered_set|stack|std::stack|queue|std::queue|list|std::list)\b'
        declarations = re.findall(var_types + r'\s+([a-zA-Z0-9_,\s\*\&\[\]\(\)\{\}\=\+\-\/\*]+);', self.code)
        
        variables_count = 0
        for dtype, decl_body in declarations:
            # Skip templates declarations inside class definitions
            if 'class' in decl_body or 'struct' in decl_body:
                continue
            # Split by commas (handling nested templates or functions can be hard, but this is static V1)
            # Count variables by splitting on commas not inside angle brackets or parentheses
            vars_split = self._split_by_comma_outside_braces(decl_body)
            variables_count += len(vars_split)
            
        # Account for function arguments as variables
        for func in self.functions:
            if func['params'].strip():
                params_split = func['params'].split(',')
                variables_count += len(params_split)

        # Count recursive calls
        recursive_calls = 0
        for func in self.functions:
            func_name = func['name']
            # Search for func_name( in function body
            # Handle scoped names: Solution::solve -> solve
            base_name = func_name.split('::')[-1]
            matches = re.findall(r'\b' + re.escape(base_name) + r'\b\s*\(', func['body'])
            recursive_calls += len(matches)

        code_lines = self.total_lines - self.blank_lines - self.comment_lines_count
        
        return {
            "lines_total": self.total_lines,
            "lines_code": max(0, code_lines),
            "lines_comment": self.comment_lines_count,
            "lines_blank": self.blank_lines,
            "functions_count": len(self.functions),
            "loops_count": total_loops,
            "recursive_calls": recursive_calls,
            "if_statements": if_count,
            "variables_count": variables_count
        }

    def _split_by_comma_outside_braces(self, s: str) -> list:
        """
        Splits a declaration string by comma, but only if the comma is not
        inside template brackets < > or parentheses ( ).
        """
        parts = []
        current = []
        angle_depth = 0
        paren_depth = 0
        for char in s:
            if char == '<':
                angle_depth += 1
                current.append(char)
            elif char == '>':
                angle_depth = max(0, angle_depth - 1)
                current.append(char)
            elif char == '(':
                paren_depth += 1
                current.append(char)
            elif char == ')':
                paren_depth = max(0, paren_depth - 1)
                current.append(char)
            elif char == ',' and angle_depth == 0 and paren_depth == 0:
                parts.append("".join(current).strip())
                current = []
            else:
                current.append(char)
        if current:
            parts.append("".join(current).strip())
        return [p for p in parts if p]

    def _parse_loops_in_body(self, body: str) -> list:
        """
        Extracts loop start/end scopes and headers inside a function body.
        Correctly parses do-while loops first and avoids double-counting their trailing while statement.
        
        Returns:
            list: List of dicts with loop type, header, start_idx, end_idx.
        """
        loops = []
        parsed_ranges = []
        
        # 1. Parse do-while loops first
        # do { ... } while (cond);
        for match in re.finditer(r'\bdo\b', body):
            start_search = body.find('{', match.end())
            if start_search != -1:
                brace_end = find_matching_brace(body, start_search)
                if brace_end != -1:
                    # Find trailing while (cond);
                    while_match = re.search(r'\bwhile\s*\(', body[brace_end:])
                    if while_match:
                        while_start_in_body = brace_end + while_match.start()
                        paren_count = 0
                        semi_idx = -1
                        # Traverse to match parenthesis
                        for k in range(while_start_in_body + (while_match.end() - while_match.start() - 1), len(body)):
                            if body[k] == '(':
                                paren_count += 1
                            elif body[k] == ')':
                                paren_count -= 1
                                if paren_count == 0:
                                    # Find matching semicolon
                                    semi_idx = body.find(';', k)
                                    break
                        if semi_idx != -1:
                            header = "do ... " + body[while_start_in_body:semi_idx+1]
                            loops.append({
                                "type": "do-while",
                                "header": header,
                                "start_idx": match.start(),
                                "end_idx": semi_idx
                            })
                            parsed_ranges.append((match.start(), semi_idx))
                            
        # 2. Parse for and while loops
        for match in re.finditer(r'\b(for|while)\b\s*\(', body):
            start_idx = match.start()
            
            # Skip if this is the trailing 'while' of a do-while loop
            is_do_while_tail = False
            for r_start, r_end in parsed_ranges:
                if r_start < start_idx < r_end:
                    is_do_while_tail = True
                    break
            if is_do_while_tail:
                continue
                
            loop_type = match.group(1)
            start_search = match.end() - 1 # starts at '('
            
            # Find closing paren matching the '('
            paren_count = 0
            end_paren_idx = -1
            for k in range(start_search, len(body)):
                if body[k] == '(':
                    paren_count += 1
                elif body[k] == ')':
                    paren_count -= 1
                    if paren_count == 0:
                        end_paren_idx = k
                        break
            
            if end_paren_idx != -1:
                header = body[match.start():end_paren_idx+1]
                remainder = body[end_paren_idx+1:].strip()
                if remainder.startswith('{'):
                    brace_start = body.find('{', end_paren_idx)
                    brace_end = find_matching_brace(body, brace_start)
                    if brace_end != -1:
                        loops.append({
                            "type": loop_type,
                            "header": header,
                            "start_idx": match.start(),
                            "end_idx": brace_end
                        })
                else:
                    semi_idx = body.find(';', end_paren_idx)
                    if semi_idx != -1:
                        loops.append({
                            "type": loop_type,
                            "header": header,
                            "start_idx": match.start(),
                            "end_idx": semi_idx
                        })
        return loops

    def _estimate_complexities(self) -> tuple:
        """
        Estimates the Time and Space complexity of the code.
        Analyzes each function independently and takes the worst-case.
        
        Returns:
            tuple: (time_complexity_str, space_complexity_str)
        """
        if not self.functions:
            self.complexity_explanation.append("No user-defined functions found. Assuming simple procedural code.")
            time_comp, space_comp = self._analyze_raw_procedural_code()
            return time_comp, space_comp
            
        # Build call graph for mutual recursion detection
        call_graph = {}
        mutually_recursive = set()
        for func in self.functions:
            func_name = func['name']
            base_name = func_name.split('::')[-1]
            call_graph[base_name] = []
            body_code = func['body']
            for other_func in self.functions:
                other_name = other_func['name'].split('::')[-1]
                if other_name != base_name:
                    if re.search(r'\b' + re.escape(other_name) + r'\b\s*\(', body_code):
                        call_graph[base_name].append(other_name)
                        
        for f1 in call_graph:
            for f2 in call_graph[f1]:
                if f1 in call_graph.get(f2, []):
                    mutually_recursive.add(f1)
                    mutually_recursive.add(f2)

        function_complexities = []
        
        for func in self.functions:
            func_name = func['name']
            body = func['body']
            
            self.complexity_explanation.append(f"Analyzing function `{func_name}`:")
            
            # 1. Parse loops in the function body
            loops = self._parse_loops_in_body(body)
            
            # 2. Analyze nesting
            loop_complexities = []
            for loop in loops:
                # Determine nesting depth
                # Nesting depth is how many loops in loops contain this loop
                parent_count = 0
                for other in loops:
                    if other != loop and other['start_idx'] < loop['start_idx'] and other['end_idx'] > loop['end_idx']:
                        parent_count += 1
                
                # Estimate individual loop base complexity
                base_complexity = self._estimate_loop_base_complexity(loop['header'], body[loop['start_idx']:loop['end_idx']])
                loop_complexities.append({
                    "loop": loop,
                    "depth": parent_count,
                    "base": base_complexity
                })
                
            # Compute cumulative loop time complexity
            max_loop_complexity = "O(1)"
            
            if loop_complexities:
                # Group loops by nesting paths
                # To simplify: we can sum base complexities along nesting branches.
                # For static analysis, the time complexity is the max of (multiplied nested paths).
                # Find maximum nesting paths:
                # Let's map parents:
                paths = {}
                for lc in loop_complexities:
                    depth = lc['depth']
                    base = lc['base']
                    # We can approximate: if nested, multiply complexities
                    if depth not in paths:
                        paths[depth] = []
                    paths[depth].append(base)
                
                # Multiply nested loops: O(n^depth)
                # Let's track:
                # Max depth:
                max_depth = max(paths.keys()) if paths else 0
                
                # Walk through layers and combine complexities
                # If there are nested loops, multiply them
                # E.g. Outer loop depth 0 is O(n), Inner loop depth 1 is O(n) -> O(n²)
                path_complexities = []
                
                # Check for nesting layers:
                if 0 in paths:
                    for base0 in paths[0]:
                        current_c = base0
                        # Check nested loops inside this specific outer loop:
                        outer_loop = next(lc['loop'] for lc in loop_complexities if lc['depth'] == 0 and lc['base'] == base0)
                        
                        # Find inner loops
                        nested_inner = [lc for lc in loop_complexities if lc['depth'] > 0 and lc['loop']['start_idx'] > outer_loop['start_idx'] and lc['loop']['end_idx'] < outer_loop['end_idx']]
                        
                        if nested_inner:
                            # Graph traversal BFS/DFS heuristic:
                            # If outer is queue/stack loop, and inner is adjacency list traversal,
                            # it runs in O(V+E) = O(n) time.
                            is_graph_traversal = False
                            outer_header = outer_loop["header"]
                            if (".empty()" in outer_header or "q.front()" in body or "q.pop()" in body or "s.top()" in body or "s.pop()" in body):
                                for inner in nested_inner:
                                    inner_header = inner["loop"]["header"]
                                    if ":" in inner_header or "adj" in inner_header or "graph" in inner_header:
                                        is_graph_traversal = True
                                        break
                                        
                            if is_graph_traversal:
                                current_c = "O(n)"
                            else:
                                # Simply multiply complexities of nested loops
                                prod_c = base0
                                nested_inner.sort(key=lambda x: x['depth'])
                                for inner in nested_inner:
                                    prod_c = self._multiply_complexities(prod_c, inner['base'])
                                current_c = prod_c
                        
                        path_complexities.append(current_c)
                
                if path_complexities:
                    max_loop_complexity = self._max_complexity(path_complexities)
                else:
                    # Fallback if depth analysis missed outer loops (e.g. malformed scopes)
                    max_loop_complexity = self._max_complexity([lc['base'] for lc in loop_complexities])

            # 3. Analyze recursion
            base_name = func_name.split('::')[-1]
            rec_matches = len(re.findall(r'\b' + re.escape(base_name) + r'\b\s*\(', body))
            
            is_mutually_recursive = base_name in mutually_recursive
            is_recursive = rec_matches > 0 or is_mutually_recursive
            is_multiple_recursion = rec_matches >= 2
            
            func_time_comp = max_loop_complexity
            func_space_comp = "O(1)"
            
            # Estimate recursion complexity
            if is_recursive:
                # Check parameter reduction: linear (n-1) vs divide and conquer (n/2)
                reduction_type = "linear"
                if "/2" in body or "/ 2" in body or "%" in body or ">> 1" in body or ">>= 1" in body or "partition" in body or "pivot" in body:
                    reduction_type = "divide"
                
                if is_multiple_recursion:
                    if reduction_type == "divide":
                        # E.g. Merge sort pattern
                        func_time_comp = "O(n log n)"
                        func_space_comp = "O(log n)"
                        self.complexity_explanation.append(
                            f"- Detected multiple recursion with divide-and-conquer (e.g. `n/2`) in `{func_name}`. Time: O(n log n), Space: O(log n) call stack."
                        )
                    else:
                        # E.g. Fibonacci: O(2^n)
                        func_time_comp = "O(2^n)"
                        func_space_comp = "O(n)"
                        self.complexity_explanation.append(
                            f"- Detected multiple recursion with linear reduction (e.g. `n-1`) in `{func_name}`. Time: O(2^n) (exponential), Space: O(n) call stack depth."
                        )
                else:
                    if reduction_type == "divide":
                        func_time_comp = "O(log n)"
                        func_space_comp = "O(log n)"
                        self.complexity_explanation.append(
                            f"- Detected single recursion with divide-and-conquer in `{func_name}`. Time: O(log n), Space: O(log n) call stack."
                        )
                    else:
                        func_time_comp = "O(n)"
                        func_space_comp = "O(n)"
                        self.complexity_explanation.append(
                            f"- Detected single recursion with linear reduction in `{func_name}`. Time: O(n), Space: O(n) call stack."
                        )
            else:
                # Add loop comments to explanation
                if loops:
                    self.complexity_explanation.append(
                        f"- Found {len(loops)} loops. Maximum nested loop depth complexity estimated as {max_loop_complexity}."
                    )
                else:
                    self.complexity_explanation.append("- No loops or recursion detected. Constant time complexity O(1).")

            # 4. Check sorting or search functions
            if "std::sort" in body or "sort(" in body:
                func_time_comp = self._max_complexity([func_time_comp, "O(n log n)"])
                self.complexity_explanation.append(f"- Detected sorting operation (`std::sort`). Elevating complexity to O(n log n).")
                
            if "std::binary_search" in body or "binary_search(" in body or "lower_bound(" in body or "upper_bound(" in body:
                if func_time_comp == "O(1)":
                    func_time_comp = "O(log n)"
                    self.complexity_explanation.append(f"- Detected STL binary search usage. Time complexity: O(log n).")

            # Space complexity from containers declared inside the function
            container_space = self._estimate_container_space(body)
            func_space_comp = self._max_complexity([func_space_comp, container_space])
            if container_space != "O(1)":
                self.complexity_explanation.append(f"- Memory structures (vectors/maps) declared inside function. Space: {container_space}.")
            
            function_complexities.append((func_time_comp, func_space_comp))
            self.complexity_explanation.append(f"Result for `{func_name}`: Time {func_time_comp} | Space {func_space_comp}\n")
            
        # Select maximum of all function complexities
        final_time = self._max_complexity([fc[0] for fc in function_complexities])
        final_space = self._max_complexity([fc[1] for fc in function_complexities])
        
        # Check global container declarations (outside functions, e.g. class variables)
        global_space = self._estimate_container_space(self.code)
        final_space = self._max_complexity([final_space, global_space])
        
        self.complexity_explanation.append(f"Overall complexity summary:")
        self.complexity_explanation.append(f"- Time Complexity: {final_time}")
        self.complexity_explanation.append(f"- Space Complexity: {final_space}")
        
        return final_time, final_space

    def _analyze_raw_procedural_code(self) -> tuple:
        """
        Fallback analysis for simple programs that do not define functions (e.g. raw main scripts).
        """
        loops = self._parse_loops_in_body(self.code)
        max_loop_c = "O(1)"
        
        if loops:
            loop_complexities = [self._estimate_loop_base_complexity(l['header'], self.code[l['start_idx']:l['end_idx']]) for l in loops]
            max_loop_c = self._max_complexity(loop_complexities)
            self.complexity_explanation.append(f"Found {len(loops)} loops in procedural code. Complexity: {max_loop_c}.")
        else:
            self.complexity_explanation.append("No loops detected. Complexity: O(1).")
            
        if "std::sort" in self.code or "sort(" in self.code:
            max_loop_c = self._max_complexity([max_loop_c, "O(n log n)"])
            self.complexity_explanation.append("Detected sorting operation (`std::sort`). Time Complexity: O(n log n).")

        space_c = self._estimate_container_space(self.code)
        self.complexity_explanation.append(f"Estimated Space Complexity: {space_c}.")
        
        return max_loop_c, space_c

    def _estimate_loop_base_complexity(self, header: str, body: str) -> str:
        """
        Analyzes a single loop header to estimate its time complexity (O(1), O(log n), O(n)).
        
        Args:
            header (str): The loop declaration (e.g., 'for(int i=0; i<n; i++)')
            body (str): The statements inside the loop.

        Returns:
            str: complexity notation ('O(1)', 'O(log n)', or 'O(n)').
        """
        # Clean header
        header = header.strip()
        
        # Constant limits e.g., for(int i=0; i<10; i++)
        # Matches numbers inside loop condition checks
        # Examples: i < 100, i <= 5
        # If there are variables like n, size(), length(), we assume dynamic
        dynamic_indicators = r'\b(n|m|k|sz|size|length|len|limit|N|M|K)\b'
        
        if 'for' in header:
            # Split for header into 3 sections
            # for (init; cond; incr)
            sections = header.split(';')
            if len(sections) == 3:
                cond = sections[1].strip()
                incr = sections[2].strip()
                
                # Check empty condition (e.g., for(;;))
                if not cond:
                    return "O(infinity)"
                
                # Check increment
                # Logarithmic: i *= 2, i /= 2, i >>= 1, i <<= 1
                if any(op in incr for op in ('*=', '/=', '<<=', '>>=')) or ('*' in incr or '/' in incr) and any(x in incr for x in ('2', '3', '4')):
                    return "O(log n)"
                
                # Constant bounds
                if not re.search(dynamic_indicators, cond) and re.search(r'\b\d+\b', cond):
                    return "O(1)"
                    
        elif 'while' in header:
            # Check while condition
            cond = header
            # Check if condition is constant
            if re.search(r'\b(true|1)\b', cond):
                # If infinite loop, check if there's a break
                if 'break' not in body:
                    return "O(infinity)"
                    
            # Check if variables inside body are divided (indicating binary reduction)
            # e.g., n /= 2 or n = n / 2
            if any(op in body for op in ('/=', '>>=')) and re.search(r'\b(n|size|length)\b', body):
                return "O(log n)"
                
            # Check if binary search pattern (dividing search space in half) is present
            if ('low' in body or 'high' in body or 'left' in body or 'right' in body) and 'mid' in body and ('/ 2' in body or '/2' in body):
                return "O(log n)"
                
            if not re.search(dynamic_indicators, cond) and re.search(r'\b\d+\b', cond):
                # If checking a low constant like 0, 1, or 2 as a lower bound limit,
                # it is likely a countdown loop (e.g. while(j >= 0)) which is dynamic.
                if re.search(r'\b(0|1|2)\b', cond) and ('>' in cond or '>=' in cond or '!=' in cond):
                    return "O(n)"
                return "O(1)"
                
        return "O(n)"

    def _estimate_container_space(self, code_segment: str) -> str:
        """
        Estimates the space complexity based on C++ structures/containers allocated.
        Ignores reference parameters (e.g. vector<int>&) to calculate auxiliary space accurately.
        
        Returns:
            str: O(1), O(n), or O(n^2).
        """
        # 1. 2D Vector or 2D Array declarations (excluding references)
        # e.g., vector<vector<int>> matrix or int grid[n][n]
        if re.search(r'vector\s*<\s*vector\s*<[^>]*>>(?!\s*&)', code_segment) or re.search(r'\[\s*(n|N|m|M|size|sz)\s*\]\s*\[\s*(n|N|m|M|size|sz)\s*\]', code_segment):
            return "O(n²)"
            
        # 2. 1D Containers or 1D Arrays (excluding references)
        # E.g. vector<int> v(n) (not followed by &) or int arr[n]
        container_pattern = r'\b(vector|map|unordered_map|set|unordered_set|list|queue|priority_queue|stack|deque|pair)\s*<[^>]*>(?!\s*&)'
        array_declaration = r'\[\s*(n|N|m|M|size|sz)\s*\]'
        
        if re.search(container_pattern, code_segment) or re.search(array_declaration, code_segment):
            return "O(n)"
            
        return "O(1)"

    def _multiply_complexities(self, c1: str, c2: str) -> str:
        """
        Multiplies two complexity classes.
        E.g. O(n) * O(n) = O(n^2)
        """
        orders = {
            "O(1)": 0,
            "O(log n)": 1,
            "O(n)": 2,
            "O(n log n)": 3,
            "O(n²)": 4,
            "O(n³)": 5,
            "O(2^n)": 6,
            "O(infinity)": 7
        }
        
        # Reverse map
        rev_orders = {v: k for k, v in orders.items()}
        
        # If any is infinity or constant
        if c1 == "O(1)": return c2
        if c2 == "O(1)": return c1
        if "infinity" in c1 or "infinity" in c2: return "O(infinity)"
        
        # Multiplications mapping
        if c1 == "O(log n)" and c2 == "O(log n)": return "O(log n)" # log n * log n is small, keep O(log n) or O(log^2 n) as O(log n) for simplicity
        if (c1 == "O(n)" and c2 == "O(log n)") or (c1 == "O(log n)" and c2 == "O(n)"): return "O(n log n)"
        
        # Powers of n
        if c1 == "O(n)" and c2 == "O(n)": return "O(n²)"
        if (c1 == "O(n²)" and c2 == "O(n)") or (c1 == "O(n)" and c2 == "O(n²)"): return "O(n³)"
        if c1 == "O(n²)" and c2 == "O(n²)": return "O(2^n)" # very high, cap at 2^n
        
        # If exponential is involved
        if c1 == "O(2^n)" or c2 == "O(2^n)": return "O(2^n)"
        
        # General fallback: pick max
        return self._max_complexity([c1, c2])

    def _max_complexity(self, complexities: list) -> str:
        """
        Finds the maximum complexity class in a list of complexities.
        """
        if not complexities:
            return "O(1)"
            
        orders = {
            "O(1)": 0,
            "O(log n)": 1,
            "O(n)": 2,
            "O(n log n)": 3,
            "O(n²)": 4,
            "O(n³)": 5,
            "O(2^n)": 6,
            "O(infinity)": 7
        }
        
        # Find complexity with highest rank
        max_rank = -1
        max_val = "O(1)"
        for c in complexities:
            rank = orders.get(c, 0)
            if rank > max_rank:
                max_rank = rank
                max_val = c
        return max_val

    def _detect_patterns(self):
        """
        Identifies architectural patterns and structural features in the code.
        """
        # Nested loops check
        # We can scan the functions and check if any loop has parent depth > 0
        has_nested = False
        for func in self.functions:
            loops = self._parse_loops_in_body(func['body'])
            for loop in loops:
                # Check if loop is nested inside another loop
                for other in loops:
                    if other != loop and other['start_idx'] < loop['start_idx'] and other['end_idx'] > loop['end_idx']:
                        has_nested = True
                        break
        if has_nested:
            self.patterns.append("Nested loops")
            
        # Infinite loops check
        if "O(infinity)" in self.time_complexity or re.search(r'\bwhile\s*\(\s*(true|1)\s*\)', self.code) or re.search(r'\bfor\s*\(\s*;\s*;\s*\)', self.code):
            # Double check if there are breaks
            if "break" not in self.code:
                self.patterns.append("Infinite loops")

        # Deep nesting check
        # Match nesting brackets depth >= 4
        current_depth = 0
        max_depth = 0
        for char in self.code:
            if char == '{':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == '}':
                current_depth = max(0, current_depth - 1)
        if max_depth >= 4:
            self.patterns.append("Deep nesting")

        # Recursion and multiple recursion checks
        has_recursion = self.global_stats.get("recursive_calls", 0) > 0
        has_mult_recursion = False
        
        for func in self.functions:
            base_name = func['name'].split('::')[-1]
            matches = len(re.findall(r'\b' + re.escape(base_name) + r'\b\s*\(', func['body']))
            if matches >= 2:
                has_mult_recursion = True
                break
                
        if has_recursion:
            self.patterns.append("Recursion")
        if has_mult_recursion:
            self.patterns.append("Multiple recursion")

        # Linear Search check
        # Look for loops containing an if condition that returns/breaks
        if re.search(r'\bfor\b.*\{\s*if\s*\(.*==.*\)\s*(return|break)', self.code, re.DOTALL):
            self.patterns.append("Linear search")
            
        # Binary Search check
        # Look for mid calculations or STL binary search functions
        if "binary_search" in self.code or "lower_bound" in self.code or "upper_bound" in self.code or (("low" in self.code or "left" in self.code) and ("high" in self.code or "right" in self.code) and ("mid" in self.code or "/ 2" in self.code or "/2" in self.code)):
            self.patterns.append("Binary search")

        # Hash map usage
        if "unordered_map" in self.code or "unordered_set" in self.code:
            self.patterns.append("Hash map usage")

        # STL usage
        stl_containers = ('vector', 'map', 'set', 'list', 'stack', 'queue', 'deque', 'pair', 'unordered_map', 'unordered_set')
        if any(container in self.code for container in stl_containers):
            self.patterns.append("STL usage")

        # Sorting algorithms
        if "std::sort" in self.code or "sort(" in self.code or (has_nested and ("swap(" in self.code or "temp =" in self.code) and (">" in self.code or "<" in self.code)):
            self.patterns.append("Sorting algorithms")

    def _generate_suggestions(self):
        """
        Generates optimizations suggestions based on patterns and statistics.
        """
        # Suggestion 1: Nested Loops lookup
        if "Nested loops" in self.patterns:
            self.suggestions.append({
                "issue": "Nested loops detected.",
                "solution": "Consider using std::unordered_map or std::unordered_set to cache values, which can reduce your search time complexity from O(n²) to O(n)."
            })
            
        # Suggestion 2: Repeated Linear Search
        if "Linear search" in self.patterns and "Nested loops" in self.patterns:
            self.suggestions.append({
                "issue": "Repeated linear search inside loops.",
                "solution": "Use binary search (std::binary_search) after sorting, or preload elements into a hash table (std::unordered_set) for O(1) average access times."
            })
            
        # Suggestion 3: Sorting efficiency
        if "Sorting algorithms" in self.patterns and not ("std::sort" in self.code or "sort(" in self.code):
            self.suggestions.append({
                "issue": "Manual sorting detected (bubble/selection sort likely).",
                "solution": "Consider replacing manual nested loop sorting with C++ standard library sort: std::sort(vec.begin(), vec.end()), which runs in highly optimized O(n log n) average time."
            })

        # Suggestion 4: Recursion stack overflow
        if "Recursion" in self.patterns and not ("Multiple recursion" in self.patterns):
            self.suggestions.append({
                "issue": "Linear recursion detected.",
                "solution": "Ensure you have a well-defined base case to avoid stack overflow. Consider rewriting as an iterative loop to achieve O(1) space complexity instead of O(n) stack memory."
            })
            
        # Suggestion 5: Multiple Recursion / Fibonacci
        if "Multiple recursion" in self.patterns:
            self.suggestions.append({
                "issue": "Exponential recursion (multiple recursive calls) detected.",
                "solution": "Consider using Dynamic Programming (memoization or tabulation) to store intermediate results, reducing time complexity from exponential O(2^n) to linear O(n)."
            })

        # Suggestion 6: Object copying
        # Check if objects are passed by value in params: E.g., void func(vector<int> v)
        # Matches types vector, string, map, set followed by name without const and without &
        if re.search(r'\b(vector|string|map|set|unordered_map|unordered_set)\b\s+[a-zA-Z0-9_]+(\s*,\s*|\s*\))', self.code):
            self.suggestions.append({
                "issue": "Large objects might be passed by value in function parameters.",
                "solution": "Pass large structures (like std::vector or std::string) by const reference (e.g., const std::vector<int>& vec) to avoid expensive copy operations."
            })

        # Suggestion 7: std::endl buffer flush
        if "std::endl" in self.raw_code or "endl" in self.raw_code:
            self.suggestions.append({
                "issue": "Use of std::endl detected.",
                "solution": "Use '\\n' instead of std::endl to output newlines. std::endl forces a buffer flush which significantly slows down standard input/output operations."
            })

        # Suggestion 8: Map vs Unordered Map
        if "std::map" in self.code or "map<" in self.code:
            self.suggestions.append({
                "issue": "std::map detected.",
                "solution": "Consider using std::unordered_map instead of std::map if you do not require keys to be sorted. std::unordered_map provides O(1) average lookup times compared to O(log n) for std::map."
            })

    def _cc_for_block(self, block_text: str) -> tuple:
        """
        Calculates cyclomatic complexity for a given code block.
        Baseline is 1, incremented by branching statements.
        """
        complexity = 1
        breakdown = []
        
        # Decision point matches
        ifs = len(re.findall(r'\bif\b', block_text))
        loops = len(re.findall(r'\b(for|while|do)\b', block_text))
        do_whiles = len(re.findall(r'\bdo\b', block_text))
        cases = len(re.findall(r'\bcase\b', block_text))
        catches = len(re.findall(r'\bcatch\b', block_text))
        logicals = len(re.findall(r'&&|\|\|', block_text))
        
        complexity += ifs + loops + cases + catches + logicals - do_whiles
        
        if ifs > 0: breakdown.append(f"{ifs} conditional branches ('if')")
        if loops > 0: breakdown.append(f"{loops} loops ('for', 'while', 'do-while')")
        if cases > 0: breakdown.append(f"{cases} switch cases")
        if catches > 0: breakdown.append(f"{catches} try-catch blocks")
        if logicals > 0: breakdown.append(f"{logicals} logical junctions ('&&', '||')")
        
        return complexity, breakdown

    def _calculate_cyclomatic_complexity(self) -> dict:
        """
        Calculates the Cyclomatic Complexity across all functions, or for raw script.
        """
        overall_complexity = 0
        details = []
        
        if self.functions:
            for func in self.functions:
                comp, breakdown = self._cc_for_block(func["body"])
                overall_complexity += comp
                
                # Risk assessment per function
                if comp <= 10:
                    risk = "Low Risk"
                elif comp <= 20:
                    risk = "Moderate Risk"
                elif comp <= 50:
                    risk = "High Risk"
                else:
                    risk = "Very High Risk"
                    
                details.append({
                    "name": func["name"],
                    "complexity": comp,
                    "risk": risk,
                    "breakdown": breakdown
                })
        else:
            overall_complexity, breakdown = self._cc_for_block(self.code)
            details.append({
                "name": "global/procedural",
                "complexity": overall_complexity,
                "risk": "Low Risk" if overall_complexity <= 10 else ("Moderate Risk" if overall_complexity <= 20 else "High Risk"),
                "breakdown": breakdown
            })
            
        # Overall risk calculation
        avg_comp = overall_complexity / len(details) if details else 1
        if avg_comp <= 10:
            overall_risk = "Low Risk"
            risk_desc = "Code is simple, clear, and highly testable."
        elif avg_comp <= 20:
            overall_risk = "Moderate Risk"
            risk_desc = "Moderately complex code structure. Moderate testing effort required."
        elif avg_comp <= 50:
            overall_risk = "High Risk"
            risk_desc = "Complex code structure. High risk of defects. Refactoring recommended."
        else:
            overall_risk = "Very High Risk"
            risk_desc = "Extremely complex code. Untestable structure. Refactoring critical."
            
        return {
            "overall_value": overall_complexity,
            "risk_level": overall_risk,
            "explanation": risk_desc,
            "details": details
        }

    def _get_max_nesting_depth(self, block_text: str) -> int:
        """
        Helper to scan brace depth.
        """
        current = 0
        max_depth = 0
        in_string = False
        in_char = False
        escape = False
        for char in block_text:
            if in_string:
                if escape: escape = False
                elif char == '\\': escape = True
                elif char == '"': in_string = False
            elif in_char:
                if escape: escape = False
                elif char == '\\': escape = True
                elif char == "'": in_char = False
            else:
                if char == '"': in_string = True
                elif char == "'": in_char = True
                elif char == '{':
                    current += 1
                    max_depth = max(max_depth, current)
                elif char == '}':
                    current = max(0, current - 1)
        return max_depth

    def _detect_global_variables(self) -> list:
        """
        Checks for non-const global scope variables.
        """
        globals_list = []
        global_code = self.code
        
        # Replace function bodies to search exclusively outside functions
        sorted_funcs = sorted(self.functions, key=lambda x: x['start_idx'], reverse=True)
        for func in sorted_funcs:
            global_code = global_code[:func['start_idx']] + "{}" + global_code[func['end_idx']+1:]
            
        var_types = r'\b(int|double|float|char|string|bool|long|short|unsigned|vector|std::vector|map|std::map|unordered_map|std::unordered_map|set|std::set|unordered_set|std::unordered_set)\b'
        declarations = re.findall(var_types + r'\s+([a-zA-Z0-9_,\s\*\&\[\]\(\)\{\}\=\+\-\/\*]+);', global_code)
        
        for dtype, decl_body in declarations:
            if any(kw in decl_body for kw in ('using', 'namespace', 'class', 'struct', 'enum')):
                continue
            if 'const' in dtype or 'const' in decl_body or 'constexpr' in decl_body:
                continue
                
            vars_split = self._split_by_comma_outside_braces(decl_body)
            for var in vars_split:
                name_match = re.match(r'^\*?\s*([a-zA-Z0-9_]+)', var.strip())
                if name_match:
                    var_name = name_match.group(1)
                    globals_list.append(var_name)
                    
        return globals_list

    def _detect_code_smells(self) -> list:
        """
        Scans code for common C++ code smells.
        """
        smells = []
        
        # 1. Globals
        global_vars = self._detect_global_variables()
        for g_var in global_vars:
            smells.append({
                "type": "Global Variable",
                "details": f"Mutable global variable `{g_var}` detected. Global scope mutable states violate encapsulation and make debugging difficult.",
                "severity": "Medium"
            })
            
        # 2. Magic Numbers
        # Match float and integers. Filter out 0, 1, 2, -1, 10
        magic_nums = re.findall(r'\b(?<!\.)(3[0-9]|[4-9]\d|\d{2,}|[3-9])(?!\.)\b|\b\d+\.\d+\b', self.code)
        for num in set(magic_nums):
            # Clean tuple match
            val = num[0] if isinstance(num, tuple) else num
            if not val:
                continue
            # If literal belongs to a constant declaration, skip it
            if re.search(r'const\s+[^;]*' + re.escape(val), self.code) or re.search(r'constexpr\s+[^;]*' + re.escape(val), self.code):
                continue
            smells.append({
                "type": "Magic Number",
                "details": f"Magic literal value `{val}` hardcoded directly. Use named constants (const or constexpr) for clarity and updateability.",
                "severity": "Low"
            })
            
        for func in self.functions:
            body = func["body"]
            func_name = func["name"]
            
            # 3. Long Function
            body_lines = len(body.splitlines())
            if body_lines > 40:
                smells.append({
                    "type": "Long Function",
                    "details": f"Function `{func_name}` has {body_lines} lines of code. Functions should ideally be short (under 40 lines) and focus on a single task.",
                    "severity": "Medium"
                })
                
            # 4. Deep Nesting
            nesting_depth = self._get_max_nesting_depth(body)
            if nesting_depth >= 4:
                smells.append({
                    "type": "Deep Nesting",
                    "details": f"Brace nesting depth reaches level {nesting_depth} inside `{func_name}`. Nesting above 3 levels increases visual complexity significantly.",
                    "severity": "High"
                })
                
            # 5. Large Parameter List
            if func["params"]:
                # Split params
                p_count = len(func["params"].split(','))
                if p_count >= 4:
                    smells.append({
                        "type": "Large Parameter List",
                        "details": f"Function `{func_name}` takes {p_count} parameters. Large parameter lists make functions harder to test. Consider grouping them into a struct.",
                        "severity": "Low"
                    })
                    
            # 6. Duplicate Loops
            loops = self._parse_loops_in_body(body)
            loop_headers = [l["header"].strip().replace(" ", "") for l in loops]
            duplicates = set([h for h in loop_headers if loop_headers.count(h) > 1])
            if duplicates:
                smells.append({
                    "type": "Duplicate Loops",
                    "details": f"Detected multiple loops with identical structures in `{func_name}`. If running sequentially, consider consolidating loop bodies.",
                    "severity": "Low"
                })
                
        # 7. Infinite Loops
        if "Infinite loops" in self.patterns:
            smells.append({
                "type": "Infinite loops",
                "details": "Infinite loop detected with no apparent break path. This will cause the thread to hang indefinitely.",
                "severity": "High"
            })
                
        return smells

    def _calculate_code_quality_scores(self) -> dict:
        """
        Calculates individual categories and overall code quality metrics (0-100).
        """
        # 1. Efficiency
        efficiency = 95
        # Deduct based on time complexity
        tc_deductions = {
            "O(1)": 0,
            "O(log n)": 5,
            "O(n)": 10,
            "O(n log n)": 15,
            "O(n²)": 35,
            "O(n³)": 55,
            "O(2^n)": 75,
            "O(infinity)": 90
        }
        efficiency -= tc_deductions.get(self.time_complexity, 0)
        
        # Deduct for nested loop smells
        has_nested = "Nested loops" in self.patterns
        if has_nested:
            efficiency -= 10
            
        efficiency = max(10, min(100, efficiency))
        
        # 2. Readability
        readability = 100
        # Check comment ratio
        total_lines_safe = max(1, self.total_lines)
        comment_ratio = self.comment_lines_count / total_lines_safe
        if comment_ratio < 0.1:
            readability -= int((0.1 - comment_ratio) * 200) # up to 20 deduction
        elif comment_ratio > 0.4:
            readability -= 10
            
        # Check for long lines (>85 chars)
        long_lines = sum(1 for line in self.raw_code.splitlines() if len(line) > 85)
        readability -= min(15, long_lines * 3)
        
        # Check if function encapsulation exists
        if not self.functions and self.total_lines > 30:
            readability -= 15
            
        readability = max(20, min(100, readability))
        
        # 3. Maintainability
        maintainability = 100
        avg_cc = self.cyclomatic_complexity.get("overall_value", 1)
        if self.functions:
            avg_cc /= len(self.functions)
            
        if avg_cc > 10: maintainability -= 10
        if avg_cc > 20: maintainability -= 20
        if avg_cc > 50: maintainability -= 40
        
        # Deduct for smells
        for smell in self.code_smells:
            if smell["severity"] == "High": maintainability -= 15
            elif smell["severity"] == "Medium": maintainability -= 10
            else: maintainability -= 5
            
        maintainability = max(15, min(100, maintainability))
        
        # 4. Naming
        naming = 100
        # Scan code text for short variable names (excluding typical loops)
        # int a, b; vector<int> x; etc.
        # We can approximate by matching declarations in code
        short_names_count = 0
        for func in self.functions:
            # Look for declarations like int a; or char x;
            decls = re.findall(r'\b(int|double|float|char|string|bool)\b\s+([a-zA-Z0-9_]+)\s*;', func["body"])
            for dtype, name in decls:
                if len(name) == 1 and name not in ('i', 'j', 'k', 'x', 'y', 'z', 'c'):
                    short_names_count += 1
                    
        naming -= min(30, short_names_count * 5)
        naming = max(30, min(100, naming))
        
        # 5. Overall Score
        overall = int(0.3 * efficiency + 0.3 * maintainability + 0.25 * readability + 0.15 * naming)
        
        return {
            "overall": overall,
            "efficiency": efficiency,
            "readability": readability,
            "maintainability": maintainability,
            "naming": naming
        }

    def _calculate_confidence_score(self) -> int:
        """
        Estimates a confidence percentage (40% to 99%) on the complexity output.
        """
        confidence = 98
        
        # Deduct if pointer/memory calculations are found (adds dynamic complexity)
        if "*" in self.code or "malloc" in self.code or "new " in self.code:
            confidence -= 15
            
        # Deduct for recursion
        if "Recursion" in self.patterns:
            confidence -= 8
            
        # Deduct for template/unresolved external calls
        if "STL usage" in self.patterns:
            confidence -= 5
            
        # Deduct for very low comment density (hard to verify context)
        if self.comment_lines_count == 0:
            confidence -= 5
            
        # Deduct for complex multi-nested loops
        if "Deep nesting" in self.patterns:
            confidence -= 10
            
        return max(45, min(99, confidence))

    def get_results(self) -> dict:
        """
        Formats and returns the full analysis results in a structured dict.
        """
        return {
            "time_complexity": self.time_complexity,
            "space_complexity": self.space_complexity,
            "stats": self.global_stats,
            "patterns": self.patterns,
            "suggestions": self.suggestions,
            "explanation": "\n".join(self.complexity_explanation),
            "cyclomatic_complexity": self.cyclomatic_complexity,
            "code_smells": self.code_smells,
            "quality_scores": self.quality_scores,
            "confidence_score": self.confidence_score
        }

