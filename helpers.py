from typing import Dict, Union

def preprocess_cpp_code(code: str) -> Dict[str, Union[str, int]]:
    """Strips C++ comments (both single-line '//' and multi-line '/* ... */')
    from the source code while keeping the exact line structure (so line numbers align).
    Also counts the number of lines containing comments.

    Args:
        code: The raw C++ input code.

    Returns:
        A dictionary containing:
            - 'stripped_code' (str): Code with comments replaced by spaces/newlines.
            - 'comment_lines_count' (int): Number of lines that contained comments.
    """
    # Strip preprocessor directives to prevent macros from interfering with function parsing
    raw_lines = code.splitlines()
    cleaned_lines = []
    for line in raw_lines:
        if line.strip().startswith('#'):
            cleaned_lines.append(' ' * len(line))
        else:
            cleaned_lines.append(line)
    code = '\n'.join(cleaned_lines)

    lines = code.splitlines()
    comment_lines = set()
    
    result_chars = []
    i = 0
    n = len(code)
    
    in_line_comment = False
    in_block_comment = False
    in_string = False
    in_char = False
    escape = False

    # Keep track of current line number in the original code (0-indexed)
    current_line = 0

    while i < n:
        c = code[i]
        next_c = code[i+1] if i + 1 < n else ''

        # Handle line counting
        if c == '\n':
            current_line += 1

        if in_line_comment:
            if c == '\n':
                in_line_comment = False
                result_chars.append('\n')
            else:
                result_chars.append(' ')
            i += 1
        elif in_block_comment:
            comment_lines.add(current_line)
            if c == '*' and next_c == '/':
                in_block_comment = False
                result_chars.append('  ')
                i += 2
            elif c == '\n':
                result_chars.append('\n')
                i += 1
            else:
                result_chars.append(' ')
                i += 1
        elif in_string:
            if escape:
                escape = False
                result_chars.append(c)
                i += 1
            elif c == '\\':
                escape = True
                result_chars.append(c)
                i += 1
            elif c == '"':
                in_string = False
                result_chars.append(c)
                i += 1
            else:
                result_chars.append(c)
                i += 1
        elif in_char:
            if escape:
                escape = False
                result_chars.append(c)
                i += 1
            elif c == '\\':
                escape = True
                result_chars.append(c)
                i += 1
            elif c == "'":
                in_char = False
                result_chars.append(c)
                i += 1
            else:
                result_chars.append(c)
                i += 1
        else:
            if c == '/' and next_c == '/':
                in_line_comment = True
                comment_lines.add(current_line)
                result_chars.append('  ')
                i += 2
            elif c == '/' and next_c == '*':
                in_block_comment = True
                comment_lines.add(current_line)
                result_chars.append('  ')
                i += 2
            elif c == '"':
                in_string = True
                result_chars.append(c)
                i += 1
            elif c == "'":
                in_char = True
                result_chars.append(c)
                i += 1
            else:
                result_chars.append(c)
                i += 1

    stripped_code = "".join(result_chars)
    return {
        "stripped_code": stripped_code,
        "comment_lines_count": len(comment_lines)
    }


def find_matching_brace(code: str, start_index: int) -> int:
    """
    Finds the index of the matching closing brace '}' for the open brace '{'
    located at start_index, skipping string literals and characters.

    Args:
        code (str): The preprocessed C++ source code.
        start_index (int): The index of the opening brace '{'.

    Returns:
        int: The 0-based index of the matching brace, or -1 if not found.
    """
    brace_count = 0
    in_string = False
    in_char = False
    escape = False
    n = len(code)

    for i in range(start_index, n):
        c = code[i]
        
        if in_string:
            if escape:
                escape = False
            elif c == '\\':
                escape = True
            elif c == '"':
                in_string = False
        elif in_char:
            if escape:
                escape = False
            elif c == '\\':
                escape = True
            elif c == "'":
                in_char = False
        else:
            if c == '"':
                in_string = True
            elif c == "'":
                in_char = True
            elif c == '{':
                brace_count += 1
            elif c == '}':
                brace_count -= 1
                if brace_count == 0:
                    return i
                    
    return -1
