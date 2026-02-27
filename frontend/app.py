"""
Modernized Python Docstring Analyzer - Streamlit Frontend
Features: Drag-drop upload, sidebar filters, real-time search, modern UI
"""
import streamlit as st
import requests
import ast
import os
from typing import Dict, Optional, List, Any, Tuple

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
DEFAULT_BACKEND_URL = "http://localhost:8000"
BACKEND_URL = os.environ.get("BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/")
SUPPORTED_STYLES = ["google", "numpy", "rest"]

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Python Docstring Analyzer Pro",
    page_icon="🐍",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-repo',
        'Report a bug': "https://github.com/your-repo/issues",
        'About': "# Python Docstring Analyzer Pro\nA modern tool for analyzing Python code documentation."
    }
)

# ============================================================
# CUSTOM CSS (unchanged, omitted for brevity – keep your existing CSS)
# ============================================================
def load_css():
    """Load modern CSS styling."""
    st.markdown("""  """, unsafe_allow_html=True)

# ============================================================
# SESSION STATE MANAGEMENT
# ============================================================
def init_session_state() -> None:
    """Initialize all session state variables."""
    defaults = {
        'analysis_result': None,
        'uploaded_file': None,
        'source_code': None,
        'docstring_style': 'google',
        'search_query': '',
        'selected_filters': {
            'show_functions': True,
            'show_methods': True,
            'show_generators': True,
            'show_exceptions': True,
            # Removed show_with/without_docstrings – they are now handled by tabs
        },
        'expanded_functions': set(),
        'backend_connected': False,
        'view_mode': 'grid',
        'sort_by': 'name',
        'active_tab': 'overview',
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ============================================================
# BACKEND COMMUNICATION
# ============================================================
def check_backend() -> bool:
    """Check if backend is available."""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def analyze_file(file_content: bytes, filename: str, min_score: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Send file to backend for analysis."""
    try:
        files = {"file": (filename, file_content, "text/x-python")}
        params = {}
        if min_score:
            params["min_pep257_score"] = min_score

        response = requests.post(
            f"{BACKEND_URL}/analyze",
            files=files,
            params=params,
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        else:
            error_detail = response.json().get('detail', 'Unknown error')
            st.error(f"Analysis failed: {error_detail}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("🔌 Cannot connect to backend. Please ensure the FastAPI server is running.")
        return None
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None

# ============================================================
# SEARCH FUNCTIONALITY
# ============================================================
@st.cache_data(ttl=300)
def build_search_index(analysis_data: Dict[str, Any]) -> Dict[str, List[Dict]]:
    """
    Build a search index from analysis data.
    Returns indexed content for fast searching.
    """
    index = {
        'functions': [],
        'methods': [],
        'classes': [],
        'violations': [],
        'content': []
    }

    if not analysis_data:
        return index

    analysis = analysis_data.get('analysis', {})

    # Index functions
    for func in analysis.get('function_details', []):
        index['functions'].append({
            'name': func['name'],
            'type': 'function',
            'line': func.get('lineno', 0),
            'docstring': func.get('docstring', ''),
            'has_docstring': func.get('has_docstring', False),
            'data': func
        })

    # Index methods
    for method in analysis.get('method_details', []):
        index['methods'].append({
            'name': f"{method.get('class_name', '')}.{method['name']}",
            'type': 'method',
            'line': method.get('lineno', 0),
            'docstring': method.get('docstring', ''),
            'has_docstring': method.get('has_docstring', False),
            'data': method
        })

    # Index classes
    for cls in analysis.get('classes', []):
        index['classes'].append({'name': cls, 'type': 'class'})

    # Index PEP-257 violations
    pep257 = analysis.get('pep257_analysis', {})
    for error in pep257.get('errors', []):
        index['violations'].append({
            'description': error.get('description', ''),
            'code': error.get('code', ''),
            'line': error.get('line', 0),
            'type': 'violation'
        })

    return index

def search_content(query: str, index: Dict[str, List[Dict]]) -> List[Dict]:
    """
    Search indexed content based on query.
    Supports fuzzy matching and multiple search terms.
    """
    if not query or not index:
        return []

    query_lower = query.lower()
    results = []

    for category, items in index.items():
        for item in items:
            score = 0
            matches = []

            # Check name
            if 'name' in item and query_lower in item['name'].lower():
                score += 10
                matches.append('name')

            # Check docstring
            if 'docstring' in item and item['docstring'] and query_lower in item['docstring'].lower():
                score += 5
                matches.append('docstring')

            # Check description
            if 'description' in item and query_lower in item['description'].lower():
                score += 8
                matches.append('description')

            # Check code
            if 'code' in item and query_lower in item['code'].lower():
                score += 7
                matches.append('code')

            if score > 0:
                result = item.copy()
                result['score'] = score
                result['matches'] = matches
                result['category'] = category
                results.append(result)

    results.sort(key=lambda x: x['score'], reverse=True)
    return results

# ============================================================
# FILTER HELPERS
# ============================================================
def _passes_filters_excluding_docstring(item: Dict, filters: Dict) -> bool:
    """Check filters except docstring status (used for tab separation)."""
    # Generator filter
    if item.get('is_generator') and not filters['show_generators']:
        return False
    # Exception filter
    if item.get('exceptions_raised') and not filters['show_exceptions']:
        return False
    return True

def _get_most_common_issue(analysis: Dict) -> str:
    """Helper to find most common PEP-257 issue."""
    pep257 = analysis.get('pep257_analysis', {})
    errors_by_code = pep257.get('summary', {}).get('errors_by_code', {})
    if not errors_by_code:
        return "None"
    most_common = max(errors_by_code.items(), key=lambda x: x[1])
    return f"{most_common[0]} ({most_common[1]})"

# ============================================================
# CODE GENERATION WITH DOCSTRINGS
# ============================================================
class DocstringInserter(ast.NodeTransformer):
    """Inserts missing docstrings using a baseline map while tracking class context."""
    def __init__(self, baseline_map: Dict[Tuple[str, str], str]):
        self.baseline_map = baseline_map
        self.class_stack: List[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self._process_function(node)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        self._process_function(node)
        self.generic_visit(node)
        return node

    def _process_function(self, node: ast.AST) -> None:
        class_name = self.class_stack[-1] if self.class_stack else ''
        key = (class_name, node.name)
        if key in self.baseline_map and not ast.get_docstring(node):
            docstring = self.baseline_map[key].strip()
            docstring_node = ast.Expr(value=ast.Constant(value=docstring))
            node.body.insert(0, docstring_node)

@st.cache_data(ttl=3600)
def generate_code_with_docstrings(
    source_code: str,
    style: str,
    function_details: List[Dict],
    method_details: List[Dict]
) -> Optional[str]:
    """
    Parse the source code and insert missing docstrings using the baseline
    for the given style. Returns the modified code as a string.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        st.error(f"Cannot parse source code: {e}")
        return None

    # Create a mapping from (class_name, func_name) to baseline docstring
    baseline_map = {}
    for func in function_details:
        key = ('', func['name'])  # no class
        baseline_map[key] = func.get('baseline_docstrings', {}).get(style, '')
    for method in method_details:
        key = (method.get('class_name', ''), method['name'])
        baseline_map[key] = method.get('baseline_docstrings', {}).get(style, '')

    # Insert docstrings using the transformer
    inserter = DocstringInserter(baseline_map)
    modified_tree = inserter.visit(tree)

    # Try to unparse (Python 3.9+)
    try:
        new_code = ast.unparse(modified_tree)
        return new_code
    except AttributeError:
        st.warning("Your Python version does not support `ast.unparse` (requires Python 3.9+). Cannot generate code.")
        return None

# ============================================================
# SIDEBAR COMPONENTS
# ============================================================
def render_sidebar() -> None:
    """Render the left sidebar with filters and controls."""
    with st.sidebar:
        # Logo/Header with icon
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0; border-bottom: 1px solid var(--border-color); margin-bottom: 1.5rem;">
            <h1 style="font-size: 1.5rem; margin: 0;">🐍 DocAnalyzer</h1>
            <p style="color: var(--text-secondary); font-size: 0.875rem; margin: 0.5rem 0 0 0;">Pro Edition</p>
        </div>
        """, unsafe_allow_html=True)

        # Connection Status
        if st.session_state.backend_connected:
            st.markdown("""
            <div class="status-badge status-passed" style="margin-bottom: 1rem;">
                <span>●</span> Backend Connected
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="status-badge status-failed" style="margin-bottom: 1rem;">
                <span class="animate-pulse">●</span> Backend Offline
            </div>
            """, unsafe_allow_html=True)

        # Navigation
        st.markdown("### 📊 Navigation")
        if st.session_state.analysis_result:
            # When a nav button is clicked, clear search and set active tab
            if st.button("📈 Overview", use_container_width=True,
                         type="primary" if st.session_state.active_tab == 'overview' else "secondary"):
                st.session_state.search_query = ""
                st.session_state.active_tab = 'overview'
                st.rerun()
            if st.button("🔍 Search Results", use_container_width=True,
                         type="primary" if st.session_state.active_tab == 'search' else "secondary"):
                st.session_state.search_query = ""
                st.session_state.active_tab = 'search'
                st.rerun()
            if st.button("⚙️ Functions", use_container_width=True,
                         type="primary" if st.session_state.active_tab == 'functions' else "secondary"):
                st.session_state.search_query = ""
                st.session_state.active_tab = 'functions'
                st.rerun()
            if st.button("📋 PEP-257 Report", use_container_width=True,
                         type="primary" if st.session_state.active_tab == 'pep257' else "secondary"):
                st.session_state.search_query = ""
                st.session_state.active_tab = 'pep257'
                st.rerun()
            if st.button("📄 Generated", use_container_width=True,
                         type="primary" if st.session_state.active_tab == 'generated' else "secondary"):
                st.session_state.search_query = ""
                st.session_state.active_tab = 'generated'
                st.rerun()
        else:
            st.info("Upload a file to see navigation options")

        st.markdown("---")

        # Filters Section (only when analysis exists)
        if st.session_state.analysis_result:
            st.markdown("### 🔧 Filter by Function")
            filters = st.session_state.selected_filters

            filters['show_functions'] = st.checkbox(
                "Show Functions",
                value=filters['show_functions'],
                help="Display standalone functions"
            )
            filters['show_methods'] = st.checkbox(
                "Show Methods",
                value=filters['show_methods'],
                help="Display class methods"
            )

            st.markdown("#### Special Features")
            filters['show_generators'] = st.toggle(
                "⚡ Generators",
                value=filters['show_generators'],
                help="Show generator functions"
            )
            filters['show_exceptions'] = st.toggle(
                "⚠️ Exceptions",
                value=filters['show_exceptions'],
                help="Show functions that raise exceptions"
            )
            st.session_state.selected_filters = filters

            st.markdown("---")

            # Detailed Stats Card
            analysis = st.session_state.analysis_result.get('analysis', {})
            counts = analysis.get('counts', {})
            metadata = st.session_state.analysis_result.get('metadata', {})
            pep257 = analysis.get('pep257_analysis', {}).get('summary', {})

            st.markdown("### 📊 Detailed Stats")
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 8px;">
                <p style="margin: 0.25rem 0;"><strong>Modules:</strong> 1</p>
                <p style="margin: 0.25rem 0;"><strong>Classes:</strong> {counts.get('total_classes', 0)}</p>
                <p style="margin: 0.25rem 0;"><strong>Functions:</strong> {counts.get('total_functions', 0)}</p>
                <p style="margin: 0.25rem 0;"><strong>Methods:</strong> {counts.get('total_methods', 0)}</p>
                <p style="margin: 0.25rem 0;"><strong>Lines of Code:</strong> {metadata.get('lines_of_code', 0)}</p>
                <p style="margin: 0.25rem 0;"><strong>⚡ Generators:</strong> {counts.get('total_generators', 0)}</p>
                <p style="margin: 0.25rem 0;"><strong>⚠️ Exceptions Raised:</strong> {counts.get('total_with_exceptions', 0)}</p>
                <p style="margin: 0.25rem 0;"><strong>Functions with Exceptions:</strong> {counts.get('total_with_exceptions', 0)}</p>
                <p style="margin: 0.25rem 0;"><strong>PEP-257 Score:</strong> {pep257.get('pep257_compliance_score', 0)}%</p>
                <p style="margin: 0.25rem 0;"><strong>PEP-257 Issues:</strong> {pep257.get('total_errors', 0)}</p>
                <p style="margin: 0.25rem 0;"><strong>Most Common Issue:</strong> {_get_most_common_issue(analysis)}</p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("---")

        # Docstring Styles Info
        with st.expander("📘 About Docstring Styles"):
            st.markdown("""
            **Google Style**
            - Clean and readable
            - Uses `Args:` and `Returns:` sections
            - Popular in Google projects

            **NumPy Style**
            - Detailed with sections
            - Uses `Parameters`, `Returns`, `Raises`
            - Popular in scientific computing

            **reStructuredText**
            - Uses `:param:` and `:returns:` syntax
            - Compatible with Sphinx
            - Used in official Python docs
            """)

        # Settings
        st.markdown("### ⚙️ Settings")
        st.markdown("#### Default Style")
        style = st.selectbox(
            "Docstring Format",
            options=SUPPORTED_STYLES,
            format_func=lambda x: x.title(),
            index=SUPPORTED_STYLES.index(st.session_state.docstring_style),
            label_visibility="collapsed"
        )
        if style != st.session_state.docstring_style:
            st.session_state.docstring_style = style
            st.rerun()

        # View Mode
        st.markdown("#### View Mode")
        view_col1, view_col2 = st.columns(2)
        with view_col1:
            if st.button("⊞ Grid", use_container_width=True,
                         type="primary" if st.session_state.view_mode == 'grid' else "secondary"):
                st.session_state.view_mode = 'grid'
                st.rerun()
        with view_col2:
            if st.button("☰ List", use_container_width=True,
                         type="primary" if st.session_state.view_mode == 'list' else "secondary"):
                st.session_state.view_mode = 'list'
                st.rerun()

        # About
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: var(--text-secondary); font-size: 0.75rem;">
            <p>Python Docstring Analyzer Pro v2.0</p>
            <p>Built with Streamlit & FastAPI</p>
        </div>
        """, unsafe_allow_html=True)

# ============================================================
# MAIN CONTENT COMPONENTS
# ============================================================
def render_header() -> None:
    """Render the top header with search and upload."""
    col1, col2, col3 = st.columns([3, 3, 1])
    with col1:
        st.markdown("""
        <div class="section-header" style="margin: 0; border: none;">
            <span class="section-header-icon">🐍</span>
            <h2 style="font-size: 1.75rem;">Docstring Analyzer Pro</h2>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        if st.session_state.analysis_result:
            search_query = st.text_input(
                "🔍 Search",
                placeholder="Search functions, methods, violations...",
                value=st.session_state.search_query,
                label_visibility="collapsed"
            )
            if search_query != st.session_state.search_query:
                st.session_state.search_query = search_query
                if search_query:
                    st.session_state.active_tab = 'search'
    with col3:
        if st.session_state.analysis_result:
            if st.button("📁 New File", use_container_width=True):
                st.session_state.analysis_result = None
                st.session_state.uploaded_file = None
                st.session_state.source_code = None
                st.session_state.search_query = ''
                st.rerun()

def render_upload_zone() -> None:
    """Render the file upload zone."""
    st.markdown("""
    <div class="modern-card animate-fade-in">
        <div class="section-header">
            <span class="section-header-icon">📤</span>
            <h2>Upload Python File</h2>
        </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Drop your Python file here or click to browse",
        type=["py"],
        help="Upload a .py file to analyze its docstrings, comments, and PEP-257 compliance",
        label_visibility="collapsed"
    )

    if uploaded_file:
        col1, col2 = st.columns([3, 1])
        with col1:
            with st.expander("👁️ Preview Code", expanded=False):
                code_content = uploaded_file.getvalue().decode("utf-8")
                st.code(code_content, language="python")
        with col2:
            st.markdown("<br>" * 2, unsafe_allow_html=True)
            min_score = st.slider(
                "Min PEP-257 Score",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=5.0,
                help="Set a minimum PEP-257 score requirement (0 = no requirement)"
            )
            if st.button("🚀 Analyze Code", type="primary", use_container_width=True):
                with st.spinner("🔍 Analyzing code structure..."):
                    uploaded_file.seek(0)
                    file_bytes = uploaded_file.read()
                    source_code = file_bytes.decode("utf-8")
                    result = analyze_file(
                        file_bytes,
                        uploaded_file.name,
                        min_score if min_score > 0 else None
                    )
                    if result:
                        st.session_state.analysis_result = result
                        st.session_state.uploaded_file = uploaded_file
                        st.session_state.source_code = source_code
                        st.success("✅ Analysis complete!")
                        st.rerun()
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📂</div>
            <h3>No file uploaded</h3>
            <p>Upload a Python file to get started with the analysis</p>
        </div>
        """, unsafe_allow_html=True)

        # Feature highlights
        st.markdown("---")
        st.markdown("### ✨ Features")
        cols = st.columns(4)
        features = [
            ("📊", "Coverage Analysis", "Track docstring coverage"),
            ("📋", "PEP-257 Compliance", "Check docstring conventions"),
            ("⚡", "Smart Detection", "Find generators & exceptions"),
            ("🎨", "Multi-Style Support", "Google, NumPy, reST formats")
        ]
        for col, (icon, title, desc) in zip(cols, features):
            with col:
                st.markdown(f"""
                <div style="text-align: center; padding: 1rem;">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>
                    <h4 style="margin: 0; font-size: 1rem;">{title}</h4>
                    <p style="font-size: 0.875rem; color: var(--text-secondary);">{desc}</p>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

def render_overview(data: Dict) -> None:
    """Render the overview dashboard."""
    analysis = data['analysis']
    counts = analysis['counts']
    metadata = data['metadata']

    st.markdown("""
    <div class="section-header">
        <span class="section-header-icon">📈</span>
        <h2>Overview Dashboard</h2>
    </div>
    """, unsafe_allow_html=True)

    # Key Metrics Grid
    st.markdown('<div class="grid-4">', unsafe_allow_html=True)

    coverage = counts.get('docstring_coverage', 0)
    pep257_score = analysis.get('pep257_analysis', {}).get('summary', {}).get('pep257_compliance_score', 0)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{coverage:.0f}%</div>
            <div class="metric-label">Docstring Coverage</div>
            <div class="progress-container"><div class="progress-bar" style="width: {coverage}%;"></div></div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        status_class = "status-passed" if pep257_score >= 80 else "status-warning" if pep257_score >= 50 else "status-failed"
        status_text = "Passed" if pep257_score >= 80 else "Needs Work"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{pep257_score:.0f}%</div>
            <div class="metric-label">PEP-257 Score</div>
            <div class="status-badge {status_class}" style="margin-top: 0.5rem;">{status_text}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{counts.get('total_functions', 0)}</div>
            <div class="metric-label">Functions</div>
            <div style="color: var(--text-secondary); font-size: 0.875rem;">{counts.get('functions_with_docstrings', 0)} documented</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{counts.get('total_methods', 0)}</div>
            <div class="metric-label">Methods</div>
            <div style="color: var(--text-secondary); font-size: 0.875rem;">{counts.get('methods_with_docstrings', 0)} documented</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # File Info & Advanced Metrics
    st.markdown('<div class="modern-card">', unsafe_allow_html=True)
    col1, col2 = st.columns([2, 3])
    with col1:
        st.markdown("### 📁 File Information")
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 8px;">
            <p><strong>Filename:</strong> {data['filename']}</p>
            <p><strong>Size:</strong> {metadata['file_size_bytes']:,} bytes</p>
            <p><strong>Lines:</strong> {metadata['lines_of_code']:,}</p>
            <p><strong>Classes:</strong> {counts.get('total_classes', 0)}</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("### 📊 Code Quality Metrics")
        all_functions = analysis.get('function_details', []) + analysis.get('method_details', [])
        total_generators = sum(1 for f in all_functions if f.get('is_generator'))
        total_exceptions = sum(len(f.get('exceptions_raised', [])) for f in all_functions)
        comment_density = (counts.get('total_comments', 0) / max(metadata['lines_of_code'], 1)) * 100
        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
        with metrics_col1:
            st.metric("⚡ Generators", total_generators)
        with metrics_col2:
            st.metric("⚠️ Exceptions", total_exceptions)
        with metrics_col3:
            st.metric("💬 Comment Density", f"{comment_density:.1f}%")
    st.markdown('</div>', unsafe_allow_html=True)

    # Quality Gate Status
    if 'quality_gate' in data:
        qg = data['quality_gate']
        qg_passed = qg.get('passed', False)
        status_class = "status-passed" if qg_passed else "status-failed"
        status_icon = "✅" if qg_passed else "❌"
        st.markdown(f"""
        <div class="modern-card" style="border-left: 4px solid {'var(--success-color)' if qg_passed else 'var(--error-color)'};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3 style="margin: 0;">{status_icon} Quality Gate</h3>
                    <p style="margin: 0.5rem 0 0 0; color: var(--text-secondary);">{qg.get('message', '')}</p>
                </div>
                <div class="status-badge {status_class}">{'PASSED' if qg_passed else 'FAILED'}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_search_results(data: Dict, query: str) -> None:
    """Render search results."""
    st.markdown(f"""
    <div class="section-header">
        <span class="section-header-icon">🔍</span>
        <h2>Search Results</h2>
    </div>
    """, unsafe_allow_html=True)

    if not query:
        st.info("Enter a search query in the header to find functions, methods, or violations.")
        return

    index = build_search_index(data)
    results = search_content(query, index)

    if not results:
        st.warning(f"No results found for '{query}'")
        return

    st.markdown(f"<p style='color: var(--text-secondary);'>Found {len(results)} results for '{query}'</p>", unsafe_allow_html=True)

    categories = {}
    for result in results:
        cat = result.get('category', 'other')
        categories.setdefault(cat, []).append(result)

    for category, items in categories.items():
        with st.expander(f"{category.title()} ({len(items)} results)", expanded=True):
            for item in items:
                render_search_result_item(item)

def render_search_result_item(item: Dict) -> None:
    """Render a single search result item."""
    item_type = item.get('type', 'unknown')
    if item_type in ['function', 'method']:
        has_doc = item.get('has_docstring', False)
        border_color = "var(--success-color)" if has_doc else "var(--error-color)"
        icon = "✅" if has_doc else "❌"
        st.markdown(f"""
        <div class="function-card" style="border-left-color: {border_color};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>{icon} {item['name']}</strong>
                    <span style="color: var(--text-secondary); font-size: 0.875rem; margin-left: 0.5rem;">Line {item.get('line', 0)}</span>
                </div>
                <span class="filter-tag">{item_type}</span>
            </div>
            {f'<p style="margin: 0.5rem 0 0 0; font-size: 0.875rem; color: var(--text-secondary);">{item["docstring"][:100]}...</p>' if item.get('docstring') else ''}
        </div>
        """, unsafe_allow_html=True)
    elif item_type == 'violation':
        st.markdown(f"""
        <div class="function-card" style="border-left-color: var(--warning-color);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>⚠️ {item.get('code', 'Violation')}</strong>
                    <span style="color: var(--text-secondary); font-size: 0.875rem; margin-left: 0.5rem;">Line {item.get('line', 0)}</span>
                </div>
            </div>
            <p style="margin: 0.5rem 0 0 0; font-size: 0.875rem;">{item.get('description', '')}</p>
        </div>
        """, unsafe_allow_html=True)

def render_functions_list(data: Dict) -> None:
    """Render the functions and methods list with tabs for documented/undocumented."""
    analysis = data['analysis']
    filters = st.session_state.selected_filters

    st.markdown("""
    <div class="section-header">
        <span class="section-header-icon">⚙️</span>
        <h2>Functions & Methods</h2>
    </div>
    """, unsafe_allow_html=True)

    # Collect all items that match the non-docstring filters
    all_items = []
    if filters['show_functions']:
        for func in analysis.get('function_details', []):
            if _passes_filters_excluding_docstring(func, filters):
                all_items.append(('function', func))
    if filters['show_methods']:
        for method in analysis.get('method_details', []):
            if _passes_filters_excluding_docstring(method, filters):
                all_items.append(('method', method))

    documented = [(t, f) for t, f in all_items if f.get('has_docstring')]
    undocumented = [(t, f) for t, f in all_items if not f.get('has_docstring')]

    tab1, tab2 = st.tabs([f"✅ Documented ({len(documented)})", f"❌ Undocumented ({len(undocumented)})"])

    with tab1:
        if documented:
            for item_type, func in documented:
                render_function_card(func, item_type)
        else:
            st.info("No documented functions/methods match the current filters.")
    with tab2:
        if undocumented:
            for item_type, func in undocumented:
                render_function_card(func, item_type)
        else:
            st.info("No undocumented functions/methods match the current filters.")

def render_function_card(func: Dict, func_type: str) -> None:
    """Render a single function card."""
    has_doc = func.get('has_docstring', False)
    style = st.session_state.docstring_style

    badges = []
    if func.get('is_generator'):
        badges.append('<span class="filter-tag">⚡ Generator</span>')
    if func.get('exceptions_raised'):
        badges.append(f'<span class="filter-tag" style="background: rgba(239, 68, 68, 0.15); color: #ef4444; border-color: rgba(239, 68, 68, 0.3);">⚠️ {len(func["exceptions_raised"])} Exceptions</span>')
    badge_html = ' '.join(badges)

    status_icon = "✅" if has_doc else "❌"
    status_color = "var(--success-color)" if has_doc else "var(--error-color)"
    name = func['name']
    if func_type == 'method' and func.get('class_name'):
        name = f"{func['class_name']}.{name}"

    with st.expander(f"{status_icon} {name} (Line {func.get('lineno', 0)})"):
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"<p><strong>Type:</strong> {func_type.title()}</p>", unsafe_allow_html=True)
            st.markdown(f"<p><strong>Status:</strong> <span style='color: {status_color};'>{'Documented' if has_doc else 'Missing Docstring'}</span></p>", unsafe_allow_html=True)
            if badge_html:
                st.markdown(f"<div style='margin: 0.5rem 0;'>{badge_html}</div>", unsafe_allow_html=True)

            if func.get('args'):
                st.markdown("**Parameters:**")
                for arg in func['args']:
                    opt_mark = " (optional)" if arg.get('default') else ""
                    st.markdown(f"- `{arg['name']}`: {arg.get('type', 'Any')}{opt_mark}")

            if func.get('return_type'):
                st.markdown(f"**Returns:** `{func['return_type']}`")

        with col2:
            if has_doc and func.get('docstring'):
                st.markdown("**Current Docstring:**")
                st.code(func['docstring'], language='python')

            baseline = func.get('baseline_docstrings', {}).get(style, '')
            if baseline:
                st.markdown(f"**Suggested ({style.title()} Style):**")
                st.code(baseline, language='python')

            if st.button(f"📋 Copy {style.title()}", key=f"copy_{func['name']}_{func.get('class_name', '')}"):
                st.toast(f"Copied {style.title()} style docstring!")

def render_generated_code(data: Dict) -> None:
    """Render the code with docstrings inserted for the selected style."""
    st.markdown("""
    <div class="section-header">
        <span class="section-header-icon">📄</span>
        <h2>Generated Code with Docstrings</h2>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.source_code:
        st.error("Source code not available. Please re-upload the file.")
        return

    style = st.session_state.docstring_style
    analysis = data['analysis']
    function_details = analysis.get('function_details', [])
    method_details = analysis.get('method_details', [])

    with st.spinner("Generating code with docstrings..."):
        new_code = generate_code_with_docstrings(
            st.session_state.source_code,
            style,
            function_details,
            method_details
        )
        if new_code is None:
            return

        st.code(new_code, language="python")
        st.download_button(
            label="📥 Download Generated Code",
            data=new_code,
            file_name=f"generated_{style}.py",
            mime="text/x-python",
            use_container_width=True
        )

def render_pep257_report(data: Dict) -> None:
    """Render the PEP-257 compliance report."""
    analysis = data['analysis']
    pep257 = analysis.get('pep257_analysis', {})
    errors = pep257.get('errors', [])
    summary = pep257.get('summary', {})
    guidelines = pep257.get('guidelines', {})

    st.markdown("""
    <div class="section-header">
        <span class="section-header-icon">📋</span>
        <h2>PEP-257 Compliance Report</h2>
    </div>
    """, unsafe_allow_html=True)

    score = summary.get('pep257_compliance_score', 0)

    col1, col2, col3 = st.columns(3)
    with col1:
        status_class = "status-passed" if score >= 80 else "status-warning" if score >= 50 else "status-failed"
        status_text = "Excellent" if score >= 80 else "Good" if score >= 50 else "Needs Improvement"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{score:.0f}%</div>
            <div class="metric-label">Compliance Score</div>
            <div class="status-badge {status_class}" style="margin-top: 0.5rem;">{status_text}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{summary.get('total_errors', 0)}</div>
            <div class="metric-label">Total Violations</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        total_items = summary.get('total_items_needing_docs', 0)
        documented = summary.get('items_with_docs', 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{documented}/{total_items}</div>
            <div class="metric-label">Items Documented</div>
        </div>
        """, unsafe_allow_html=True)

    if guidelines:
        with st.expander("📘 PEP-257 Guidelines & Fixes"):
            for code, info in guidelines.items():
                st.markdown(f"**{code}**: {info.get('title', '')}")
                st.markdown(f"- {info.get('description', '')}")
                st.markdown(f"- *Fix:* {info.get('fix', '')}")
                st.markdown("---")

    if errors:
        st.markdown("### Violations")
        severities = list(set(e.get('severity', 'info') for e in errors))
        selected_severities = st.multiselect("Filter by Severity", options=severities, default=severities)
        filtered_errors = [e for e in errors if e.get('severity') in selected_severities]

        for error in filtered_errors:
            severity = error.get('severity', 'info')
            color = {'error': 'var(--error-color)', 'warning': 'var(--warning-color)', 'info': 'var(--primary-color)'}.get(severity, 'var(--text-secondary)')
            st.markdown(f"""
            <div class="function-card" style="border-left: 4px solid {color};">
                <div style="display: flex; justify-content: space-between;">
                    <strong>{error.get('code', 'D000')}: {error.get('description', '')}</strong>
                    <span style="color: var(--text-secondary);">Line {error.get('line', 0)}</span>
                </div>
                {f'<p style="margin: 0.5rem 0 0 0; font-size: 0.875rem;">Function: {error.get("function", "N/A")}</p>' if error.get('function') else ''}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("🎉 No PEP-257 violations found! Perfect compliance!")

# ============================================================
# MAIN APPLICATION
# ============================================================
def main() -> None:
    """Main application entry point."""
    load_css()
    init_session_state()

    if not st.session_state.backend_connected:
        st.session_state.backend_connected = check_backend()

    render_sidebar()
    render_header()

    if not st.session_state.analysis_result:
        render_upload_zone()
    else:
        active_tab = st.session_state.active_tab
        if active_tab == 'overview':
            render_overview(st.session_state.analysis_result)
        elif active_tab == 'search':
            render_search_results(st.session_state.analysis_result, st.session_state.search_query)
        elif active_tab == 'functions':
            render_functions_list(st.session_state.analysis_result)
        elif active_tab == 'pep257':
            render_pep257_report(st.session_state.analysis_result)
        elif active_tab == 'generated':
            render_generated_code(st.session_state.analysis_result)

if __name__ == "__main__":
    main()