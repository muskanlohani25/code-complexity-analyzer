from flask import Blueprint, render_template, request, jsonify, Response
from typing import Tuple, Union
from analyzer import CPPAnalyzer

# Create a Flask Blueprint for our routes
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index() -> str:
    """Renders the main dashboard page.

    Returns:
         The rendered HTML content of index.html.
    """
    return render_template('index.html')


@main_bp.route('/analyze', methods=['POST'])
def analyze() -> Union[Response, Tuple[Response, int]]:
    """API endpoint that accepts a JSON payload with a C++ source code string,
    analyzes it statically, and returns the complexity analysis and stats.

    Returns:
        A tuple of (JSON Response, HTTP status code) or a raw Response object.
    """
    data = request.get_json() or {}
    code = data.get('code', '')
    
    if not code.strip():
        return jsonify({
            "error": "No C++ code was provided. Please paste or enter some code to analyze."
        }), 400
        
    try:
        # Instantiate the analyzer with the incoming code
        analyzer = CPPAnalyzer(code)
        # Fetch the parsed metrics
        results = analyzer.get_results()
        return jsonify(results)
    except Exception as e:
        # Return structured error
        return jsonify({
            "error": f"Analysis failed: {str(e)}"
        }), 500
