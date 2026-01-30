# frontend/app.py
import streamlit as st
import requests
from typing import Dict, Optional, List

# Page configuration
st.set_page_config(
    page_title="Python Docstring Analyzer",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS with style selector
st.markdown("""
<style>
    .glass-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        padding: 2rem;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }

    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
    }

    .metric-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
        border-radius: 15px;
        padding: 1.5rem;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .docstring-present {
        color: #10b981;
        font-weight: bold;
    }
    
    .docstring-missing {
        color: #ef4444;
        font-weight: bold;
    }
    
    .param-list {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 10px;
        margin: 10px 0;
        font-family: monospace;
    }
    
    .baseline-docstring {
        background: rgba(59, 130, 246, 0.1);
        border-left: 4px solid #3b82f6;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        font-family: monospace;
        white-space: pre-wrap;
        max-height: 300px;
        overflow-y: auto;
    }
    
    .style-selector-container {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 20px;
        margin: 20px 0;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .style-button {
        padding: 10px 20px;
        margin: 5px;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: white;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.3s ease;
        display: inline-block;
    }
    
    .style-button:hover {
        background: rgba(255, 255, 255, 0.1);
    }
    
    .style-button.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-color: #667eea;
        color: white;
    }
    
    .comment-type {
        padding: 5px 10px;
        border-radius: 5px;
        font-size: 12px;
        font-weight: bold;
    }
    
    .single-line-comment {
        background: rgba(59, 130, 246, 0.2);
        color: #3b82f6;
    }
    
    .multi-line-comment {
        background: rgba(139, 92, 246, 0.2);
        color: #8b5cf6;
    }

    .main-header {
        text-align: center;
        padding: 3rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .docstring-style-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        margin-left: 10px;
        background: rgba(102, 126, 234, 0.2);
        color: #667eea;
    }
    
    .function-tabs {
        display: flex;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 20px;
    }
    
    .function-tab {
        padding: 10px 20px;
        cursor: pointer;
        border-bottom: 3px solid transparent;
        font-weight: 500;
    }
    
    .function-tab:hover {
        background: rgba(255, 255, 255, 0.05);
    }
    
    .function-tab.active {
        border-bottom: 3px solid #667eea;
        color: #667eea;
    }
    
    /* RAISE/YIELD DETECTION STYLES */
    .exception-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        margin-left: 8px;
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    .generator-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        margin-left: 8px;
        background: rgba(16, 185, 129, 0.2);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .exception-list {
        background: rgba(239, 68, 68, 0.05);
        border-radius: 5px;
        padding: 8px;
        margin: 5px 0;
        font-family: monospace;
        font-size: 13px;
    }
    
    .generator-info {
        background: rgba(16, 185, 129, 0.05);
        border-radius: 5px;
        padding: 8px;
        margin: 5px 0;
        font-family: monospace;
        font-size: 13px;
        border-left: 3px solid #10b981;
    }
    
    .badges-container {
        margin-bottom: 10px;
    }
    
    /* PEP-257 Styles */
    .pep257-error {
        background: rgba(239, 68, 68, 0.1);
        border-left: 4px solid #ef4444;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    
    .pep257-warning {
        background: rgba(245, 158, 11, 0.1);
        border-left: 4px solid #f59e0b;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    
    .pep257-info {
        background: rgba(59, 130, 246, 0.1);
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    
    .pep257-code {
        font-family: 'Courier New', monospace;
        background: rgba(0, 0, 0, 0.1);
        padding: 3px 6px;
        border-radius: 4px;
        font-weight: bold;
    }
    
    .pep257-line {
        font-family: monospace;
        color: #6b7280;
        font-size: 0.9em;
    }
    
    .pep257-severity-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        margin-right: 8px;
    }
    
    .severity-error {
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    .severity-warning {
        background: rgba(245, 158, 11, 0.2);
        color: #f59e0b;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    
    .severity-info {
        background: rgba(59, 130, 246, 0.2);
        color: #3b82f6;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }
    
    .compliance-score-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
        border-radius: 15px;
        padding: 1.5rem;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin: 10px 0;
    }
    
    .guideline-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #667eea;
    }
    
    /* Status Badge Styles */
    .status-passed {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        background: rgba(16, 185, 129, 0.2);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .status-failed {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    .score-status-container {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        margin-top: 10px;
    }
    
    .score-with-status {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
</style>
""", unsafe_allow_html=True)

BACKEND_URL = "http://localhost:8000"

# Initialize session state variables
if 'docstring_style' not in st.session_state:
    st.session_state.docstring_style = "google"
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "with_docstrings"
if 'active_function_tab' not in st.session_state:
    st.session_state.active_function_tab = "functions_with"


def check_backend_connection() -> bool:
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def analyze_python_file(file_content: bytes, filename: str) -> Optional[Dict]:
    try:
        files = {"file": (filename, file_content, "text/x-python")}
        response = requests.post(f"{BACKEND_URL}/analyze", files=files, timeout=10)

        if response.status_code == 200:
            return response.json()
        else:
            st.error(response.json().get("detail", "Backend error"))
            return None
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Make sure FastAPI is running.")
        return None
    except Exception as e:
        st.error(f"Error analyzing file: {str(e)}")
        return None


def get_style_description(style: str) -> str:
    """Get description for each docstring style."""
    descriptions = {
        "google": "Clean and readable format, widely used in Google projects",
        "numpy": "Detailed format with sections, popular in scientific computing",
        "rest": "reStructuredText format, used in Sphinx documentation"
    }
    return descriptions.get(style, "")


def get_score_status(score: float) -> tuple[str, str]:
    """Get status and CSS class for a given score."""
    if score >= 100:
        return "Passed", "status-passed"
    else:
        return "Failed", "status-failed"


def display_docstring_analysis(counts: Dict):
    """Display docstring statistics and analysis."""
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("Docstring Analysis")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Functions with Docstrings", 
            f"{counts['functions_with_docstrings']}/{counts['total_functions']}",
            delta=f"{counts['functions_with_docstrings'] - counts['functions_without_docstrings']}"
        )
    
    with col2:
        st.metric(
            "Methods with Docstrings",
            f"{counts['methods_with_docstrings']}/{counts['total_methods']}",
            delta=f"{counts['methods_with_docstrings'] - counts['methods_without_docstrings']}"
        )
    
    with col3:
        st.metric(
            "Total Docstring Coverage",
            f"{counts['total_with_docstrings']}/{counts['total_with_docstrings'] + counts['total_without_docstrings']}"
        )
    
    with col4:
        coverage = counts.get('docstring_coverage', 0)
        if coverage >= 80:
            delta_color = "normal"
        elif coverage >= 50:
            delta_color = "off"
        else:
            delta_color = "inverse"
        
        st.metric(
            "Coverage Percentage",
            f"{coverage:.1f}%",
            delta_color=delta_color
        )
    
    st.markdown('</div>', unsafe_allow_html=True)


def display_comment_analysis(counts: Dict):
    """Display comment statistics."""
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("Comment Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total Comments", 
            counts['total_comments']
        )
        st.caption("All # comments and triple-quoted strings")
    
    with col2:
        st.metric(
            "Single-line Comments",
            counts['single_line_comments']
        )
        st.caption("Lines starting with #")
    
    with col3:
        st.metric(
            "Multi-line Comments",
            counts['multi_line_comments']
        )
        st.caption("Triple-quoted strings (''' or \"\"\")")
    
    # Calculate comment density
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        comment_types_html = f"""
        <div style="margin-top: 20px;">
            <span class="comment-type single-line-comment">Single-line (#): {counts['single_line_comments']}</span>
            <span class="comment-type multi-line-comment" style="margin-left: 10px;">Multi-line (\"\"\"): {counts['multi_line_comments']}</span>
        </div>
        """
        st.markdown(comment_types_html, unsafe_allow_html=True)
    
    with col2:
        if counts['total_comments'] > 0:
            single_line_percent = (counts['single_line_comments'] / counts['total_comments']) * 100
            multi_line_percent = (counts['multi_line_comments'] / counts['total_comments']) * 100
            st.markdown(f"""
            <div style="margin-top: 20px;">
                <p><strong>Distribution:</strong></p>
                <p>Single-line: {single_line_percent:.1f}%</p>
                <p>Multi-line: {multi_line_percent:.1f}%</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


def display_style_selector():
    """Display docstring style selector."""
    st.markdown('<div class="style-selector-container">', unsafe_allow_html=True)
    st.markdown("#### Select Docstring Style")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Google Style", use_container_width=True, 
                     type="primary" if st.session_state.docstring_style == "google" else "secondary"):
            st.session_state.docstring_style = "google"
    
    with col2:
        if st.button("NumPy Style", use_container_width=True,
                     type="primary" if st.session_state.docstring_style == "numpy" else "secondary"):
            st.session_state.docstring_style = "numpy"
    
    with col3:
        if st.button("reStructuredText", use_container_width=True,
                     type="primary" if st.session_state.docstring_style == "rest" else "secondary"):
            st.session_state.docstring_style = "rest"
    
    # Show description
    st.markdown(f"**Selected:** {st.session_state.docstring_style.title()} Style")
    st.markdown(f"*{get_style_description(st.session_state.docstring_style)}*")
    
    st.markdown('</div>', unsafe_allow_html=True)


def display_function_details_group(functions: List[Dict], title: str, is_method: bool = False):
    """Display a group of functions/methods (either with or without docstrings)."""
    if not functions:
        st.info(f"No {title.lower()} found.")
        return
    
    for func in functions:
        # Create expander title without HTML
        expander_title = f"{func['class_name'] + '.' if is_method else ''}{func['name']}"
        
        with st.expander(expander_title):
            col1, col2 = st.columns([1, 3])
            
            with col1:
                # Show badges at the top of the left column
                badges_html = ""
                if func.get('is_generator', False):
                    badges_html += '<span class="generator-badge">⚡ Generator</span>'
                if func.get('exceptions_raised', []):
                    badges_html += f'<span class="exception-badge">⚠️ {len(func["exceptions_raised"])} Exception(s)</span>'
                
                if badges_html:
                    st.markdown(f'<div class="badges-container">{badges_html}</div>', unsafe_allow_html=True)
                
                # Docstring status
                if func['has_docstring']:
                    st.markdown('<span class="docstring-present">✅ Has Docstring</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="docstring-missing">❌ Missing Docstring</span>', unsafe_allow_html=True)
                
                # Parameters
                if func['args']:
                    st.markdown("**Parameters:**")
                    param_html = '<div class="param-list">'
                    for arg in func['args']:
                        param_type = arg.get('type', 'Any')
                        is_optional = arg.get('default', False)
                        is_vararg = arg.get('vararg', False)
                        is_kwargs = arg.get('kwargs', False)
                        
                        if is_vararg:
                            param_html += f"*{arg['name']}: {param_type}<br>"
                        elif is_kwargs:
                            param_html += f"**{arg['name']}: {param_type}<br>"
                        else:
                            optional_mark = " (optional)" if is_optional else ""
                            param_html += f"{arg['name']}: {param_type}{optional_mark}<br>"
                    param_html += '</div>'
                    st.markdown(param_html, unsafe_allow_html=True)
                
                # Return type
                if func['return_type']:
                    st.markdown(f"**Returns:** `{func['return_type']}`")
                
                # Display exceptions raised
                exceptions = func.get('exceptions_raised', [])
                if exceptions:
                    st.markdown("**Exceptions Raised:**")
                    exc_html = '<div class="exception-list">'
                    for exc in exceptions:
                        exc_html += f"• {exc}<br>"
                    exc_html += '</div>'
                    st.markdown(exc_html, unsafe_allow_html=True)
                
                # Display generator info
                if func.get('is_generator', False):
                    st.markdown('<div class="generator-info">⚡ This is a generator function (contains yield statements)</div>', unsafe_allow_html=True)
            
            with col2:
                if func['has_docstring'] and func['docstring']:
                    st.markdown(f"**Current Docstring**")
                    st.code(func['docstring'], language='python')
                    st.markdown("---")
                    st.markdown(f"**Suggested {st.session_state.docstring_style.title()} Style**")
                else:
                    st.markdown(f"**Suggested {st.session_state.docstring_style.title()} Style**")
                
                # Display the selected style docstring
                style = st.session_state.docstring_style
                baseline_docstring = func['baseline_docstrings'].get(style, "")
                st.markdown(f'<div class="baseline-docstring">{baseline_docstring}</div>', unsafe_allow_html=True)
                
                # Add copy to clipboard button
                if st.button(f"Copy {style.title()} Style", key=f"copy_{func['name']}_{func.get('class_name', '')}_{style}"):
                    st.code(baseline_docstring, language='python')
                    st.success("Copied to clipboard!")
                
                # Show other styles in expander
                with st.expander("View other styles"):
                    other_styles = {k: v for k, v in func['baseline_docstrings'].items() if k != style}
                    for other_style, other_docstring in other_styles.items():
                        st.markdown(f"**{other_style.title()} Style:**")
                        st.code(other_docstring, language='python')


def display_functions_with_tabs(function_details: List[Dict], title: str, is_method: bool = False):
    """Display functions/methods with tabs for with/without docstrings."""
    if not function_details:
        st.info(f"No {title.lower()} found.")
        return
    
    # Split functions into with and without docstrings
    functions_with_docstrings = [f for f in function_details if f['has_docstring']]
    functions_without_docstrings = [f for f in function_details if not f['has_docstring']]
    
    # Create tabs
    tab1, tab2 = st.tabs([
        f"With Docstrings ({len(functions_with_docstrings)})",
        f"Without Docstrings ({len(functions_without_docstrings)})"
    ])
    
    with tab1:
        if functions_with_docstrings:
            display_function_details_group(functions_with_docstrings, f"{title} with Docstrings", is_method)
        else:
            st.info(f"No {title.lower()} with docstrings.")
    
    with tab2:
        if functions_without_docstrings:
            display_function_details_group(functions_without_docstrings, f"{title} without Docstrings", is_method)
        else:
            st.info(f"All {title.lower()} have docstrings!")


def display_pep257_analysis(pep257_data: Dict):
    """Display PEP-257 compliance analysis results."""
    
    errors = pep257_data.get("errors", [])
    summary = pep257_data.get("summary", {})
    guidelines = pep257_data.get("guidelines", {})
    
    # Calculate compliance score
    total_errors = summary.get("total_errors", 0)
    compliance_score = max(0, 100 - (total_errors * 2))  # Simple scoring
    
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("PEP-257 Compliance Report")
    
    # Compliance score and summary with status
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Display score with status
        status_text, status_class = get_score_status(compliance_score)
        st.markdown(f"""
        <div class="score-with-status">
            <h3 style="margin: 0; font-size: 2rem;">{compliance_score:.1f}%</h3>
            <p style="margin: 5px 0; font-size: 0.9rem;">Compliance Score</p>
            <div class="{status_class}">{status_text}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.metric("Total Issues", total_errors)
    
    with col3:
        # Count by severity
        error_count = len([e for e in errors if e.get('severity') == 'error'])
        warning_count = len([e for e in errors if e.get('severity') == 'warning'])
        info_count = len([e for e in errors if e.get('severity') == 'info'])
        
        st.metric("Errors", error_count)
    
    with col4:
        st.metric("Warnings", warning_count)
    
    # Show status message
    if compliance_score >= 100:
        st.success("✅ Perfect score! All PEP-257 guidelines are followed.")
    else:
        st.warning(f"⚠️ Compliance score is {compliance_score:.1f}%. Some PEP-257 guidelines need attention.")
    
    # Error breakdown by code
    errors_by_code = summary.get("errors_by_code", {})
    if errors_by_code:
        st.markdown("---")
        st.markdown("#### Issues by Error Code")
        
        # Sort by count
        sorted_codes = sorted(errors_by_code.items(), key=lambda x: x[1], reverse=True)
        
        cols = st.columns(3)
        col_idx = 0
        
        for code, count in sorted_codes:
            guideline = guidelines.get(code, {})
            title = guideline.get("title", code)
            
            with cols[col_idx % 3]:
                st.metric(f"{code}: {title}", count)
            col_idx += 1
    
    # Show all errors if any exist
    if errors:
        st.markdown("---")
        st.markdown("#### Detailed Issues")
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        with col1:
            show_errors = st.checkbox("Show Errors", value=True)
        with col2:
            show_warnings = st.checkbox("Show Warnings", value=True)
        with col3:
            show_info = st.checkbox("Show Info", value=True)
        
        # Filter errors based on selection
        filtered_errors = [
            e for e in errors 
            if (show_errors and e.get('severity') == 'error') or
               (show_warnings and e.get('severity') == 'warning') or
               (show_info and e.get('severity') == 'info')
        ]
        
        if filtered_errors:
            for error in filtered_errors:
                display_pep257_error(error, guidelines)
        else:
            st.info("No issues match the selected filters.")
    else:
        st.markdown("---")
        st.success("✅ No PEP-257 issues found! The code is fully compliant.")
    
    # Show PEP-257 guidelines
    st.markdown("---")
    st.markdown("#### PEP-257 Guidelines Reference")
    
    # Group guidelines by category
    categories = {
        "D1xx - Missing Docstrings": [code for code in guidelines if code.startswith("D1")],
        "D2xx - Whitespace Issues": [code for code in guidelines if code.startswith("D2")],
        "D3xx - Quotes Issues": [code for code in guidelines if code.startswith("D3")],
        "D4xx - Docstring Content": [code for code in guidelines if code.startswith("D4")],
    }
    
    for category, codes in categories.items():
        with st.expander(f"{category} ({len(codes)} guidelines)"):
            for code in codes:
                if code in guidelines:
                    guideline = guidelines[code]
                    st.markdown(f"""
                    <div class="guideline-card">
                        <strong><span class="pep257-code">{code}</span>: {guideline.get('title', '')}</strong><br>
                        <small><strong>Severity:</strong> {guideline.get('severity', '').title()}</small><br>
                        <em>{guideline.get('description', '')}</em><br>
                        <small><strong>Fix:</strong> {guideline.get('fix', '')}</small>
                    </div>
                    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def display_pep257_error(error: Dict, guidelines: Dict):
    """Display a single PEP-257 error with details."""
    
    code = error.get("code", "D000")
    severity = error.get("severity", "info")
    line = error.get("line", 0)
    description = error.get("description", "")
    function = error.get("function", "")
    context = error.get("context", "")
    
    # Get guideline details
    guideline = guidelines.get(code, {})
    guideline_title = guideline.get("title", code)
    
    # Determine CSS class based on severity
    severity_class = f"pep257-{severity}"
    severity_badge_class = f"severity-{severity}"
    
    st.markdown(f"""
    <div class="{severity_class}">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <span class="pep257-severity-badge {severity_badge_class}">
                    {severity.upper()}
                </span>
                <strong><span class="pep257-code">{code}</span>: {guideline_title}</strong>
            </div>
            <span class="pep257-line">Line {line}{f' in {function}' if function else ''}</span>
        </div>
        <p>{description}</p>
        {f'<p><small><strong>Context:</strong> <code>{context}</code></small></p>' if context else ''}
    </div>
    """, unsafe_allow_html=True)


def display_analysis_results(data: Dict):
    analysis = data["analysis"]
    counts = analysis["counts"]

    st.markdown('<h1 class="main-header">Analysis Results</h1>', unsafe_allow_html=True)

    # Style selector
    display_style_selector()

    # Basic metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Modules", counts["total_modules"])
    col2.metric("Classes", counts["total_classes"])
    col3.metric("Functions", counts["total_functions"])
    col4.metric("Methods", counts["total_methods"])
    col5.metric("Lines of Code", data['metadata']['lines_of_code'])

    # RAISE/YIELD METRICS - RESTORED
    all_functions = analysis["function_details"] + analysis["method_details"]
    total_generators = sum(1 for f in all_functions if f.get('is_generator', False))
    total_exceptions = sum(len(f.get('exceptions_raised', [])) for f in all_functions)
    functions_with_exceptions = sum(1 for f in all_functions if f.get('exceptions_raised', []))
    
    col1, col2, col3 = st.columns(3)
    col1.metric("⚡ Generators", total_generators)
    col2.metric("⚠️ Exceptions Raised", total_exceptions)
    col3.metric("Functions with Exceptions", functions_with_exceptions)

    # PEP-257 compliance metrics with status
    pep257_summary = analysis.get("pep257_analysis", {}).get("summary", {})
    pep257_errors = analysis.get("pep257_analysis", {}).get("errors", [])
    
    # Calculate compliance score
    total_pep257_issues = pep257_summary.get("total_errors", 0)
    compliance_score = max(0, 100 - (total_pep257_issues * 2))
    status_text, status_class = get_score_status(compliance_score)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        # Display score with status
        st.markdown(f"""
        <div class="score-with-status">
            <h3 style="margin: 0; font-size: 2rem;">{compliance_score:.1f}%</h3>
            <p style="margin: 5px 0; font-size: 0.9rem;">PEP-257 Score</p>
            <div class="{status_class}">{status_text}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.metric("PEP-257 Issues", total_pep257_issues)
    
    with col3:
        # Show most common issue
        errors_by_code = pep257_summary.get("errors_by_code", {})
        if errors_by_code:
            most_common = max(errors_by_code.items(), key=lambda x: x[1], default=(None, 0))
            if most_common[0]:
                st.metric("Most Common Issue", f"{most_common[0]}: {most_common[1]}")
        else:
            st.metric("Most Common Issue", "None")
    
    # Show overall status message
    if compliance_score >= 100:
        st.success("🎉 Perfect PEP-257 compliance! All guidelines are followed correctly.")
    else:
        st.warning(f"⚠️ PEP-257 compliance needs improvement. Score: {compliance_score:.1f}%")

    # Comment analysis section
    display_comment_analysis(counts)
    
    # Docstring analysis section
    display_docstring_analysis(counts)

    # Detailed breakdown with tabs
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("Detailed Breakdown")
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Functions", "Methods", "Docstrings", "PEP-257 Compliance", "File Info"])

    with tab1:
        if analysis["function_details"]:
            display_functions_with_tabs(analysis["function_details"], "Functions")
        else:
            st.info("No functions found.")

    with tab2:
        if analysis["method_details"]:
            display_functions_with_tabs(analysis["method_details"], "Methods", is_method=True)
        else:
            st.info("No methods found.")

    with tab3:
        st.markdown("### Docstring Summary")
        
        # Calculate docstring coverage score
        total_functions_methods = counts['total_functions'] + counts['total_methods']
        if total_functions_methods > 0:
            coverage = counts.get('docstring_coverage', 0)
            coverage_status_text, coverage_status_class = get_score_status(coverage)
            
            st.markdown(f"""
            <div class="score-with-status">
                <h3 style="margin: 0; font-size: 2rem;">{coverage:.1f}%</h3>
                <p style="margin: 5px 0; font-size: 0.9rem;">Docstring Coverage</p>
                <div class="{coverage_status_class}">{coverage_status_text}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Functions with missing docstrings
        missing_functions = [f for f in analysis["function_details"] if not f['has_docstring']]
        missing_methods = [m for m in analysis["method_details"] if not m['has_docstring']]
        
        if missing_functions or missing_methods:
            if coverage < 100:
                st.error(f"❌ Docstring coverage is {coverage:.1f}%. Some functions/methods are missing docstrings.")
            else:
                st.warning(f"⚠️ Found {len(missing_functions)} functions and {len(missing_methods)} methods without docstrings")
            
            if missing_functions:
                st.markdown("**Functions needing docstrings:**")
                for func in missing_functions:
                    badges = []
                    if func.get('is_generator', False):
                        badges.append("⚡")
                    if func.get('exceptions_raised', []):
                        badges.append("⚠️")
                    badge_str = f" {' '.join(badges)}" if badges else ""
                    st.markdown(f"- `{func['name']}()`{badge_str}")
            
            if missing_methods:
                st.markdown("**Methods needing docstrings:**")
                for method in missing_methods:
                    badges = []
                    if method.get('is_generator', False):
                        badges.append("⚡")
                    if method.get('exceptions_raised', []):
                        badges.append("⚠️")
                    badge_str = f" {' '.join(badges)}" if badges else ""
                    st.markdown(f"- `{method['class_name']}.{method['name']}()`{badge_str}")
        else:
            st.success("✅ Perfect! All functions and methods have docstrings!")
        
        # Show coverage progress
        if total_functions_methods > 0:
            st.progress(coverage / 100)
            st.caption(f"Overall docstring coverage: {coverage:.1f}%")
        
        # Style information
        st.markdown("---")
        st.markdown("### About Docstring Styles")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Google Style**")
            st.markdown("""
            - Clean and readable
            - Uses `Args:` and `Returns:` sections
            - Popular in Google projects
            """)
        
        with col2:
            st.markdown("**NumPy Style**")
            st.markdown("""
            - Detailed with sections
            - Uses `Parameters`, `Returns`, `Raises`
            - Popular in scientific computing
            """)
        
        with col3:
            st.markdown("**reStructuredText**")
            st.markdown("""
            - Uses `:param:` and `:returns:` syntax
            - Compatible with Sphinx
            - Used in official Python docs
            """)
        
        # Information about detection features
        st.markdown("---")
        st.markdown("### Detection Features")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**⚡ Generator Detection**")
            st.markdown("""
            - Automatically detects `yield` statements
            - Identifies generator functions
            - Shows generator badge
            """)
        
        with col2:
            st.markdown("**⚠️ Exception Detection**")
            st.markdown("""
            - Detects `raise` statements
            - Lists specific exception types
            - Shows exception count
            """)
        
        with col3:
            st.markdown("**📋 PEP-257 Compliance**")
            st.markdown("""
            - Checks PEP-257 guidelines
            - Shows compliance score
            - Detailed error explanations
            """)

    # PEP-257 Compliance Tab
    with tab4:
        pep257_data = analysis.get("pep257_analysis", {})
        if pep257_data:
            display_pep257_analysis(pep257_data)
        else:
            st.info("No PEP-257 analysis data available.")

    with tab5:
        st.subheader("File Information")
        col1, col2, col3 = st.columns(3)
        col1.write(f"**Filename:** {data['filename']}")
        col2.write(f"**Size:** {data['metadata']['file_size_bytes']} bytes")
        col3.write(f"**Lines of Code:** {data['metadata']['lines_of_code']}")
        
        # Overall status summary
        st.markdown("---")
        st.markdown("### Overall Status Summary")
        
        # Calculate overall score (average of docstring coverage and PEP-257 compliance)
        docstring_coverage = counts.get('docstring_coverage', 0)
        pep257_score = max(0, 100 - (total_pep257_issues * 2))
        overall_score = (docstring_coverage + pep257_score) / 2
        overall_status_text, overall_status_class = get_score_status(overall_score)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="score-with-status">
                <h3 style="margin: 0; font-size: 2rem;">{overall_score:.1f}%</h3>
                <p style="margin: 5px 0; font-size: 0.9rem;">Overall Score</p>
                <div class="{overall_status_class}">{overall_status_text}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style="background: rgba(255, 255, 255, 0.05); border-radius: 10px; padding: 15px; margin: 10px 0; border: 1px solid rgba(255, 255, 255, 0.1);">
                <p style="margin: 0; font-size: 0.9rem;"><strong>Docstring Coverage:</strong></p>
                <h4 style="margin: 5px 0;">{docstring_coverage:.1f}%</h4>
                <div class="{get_score_status(docstring_coverage)[1]}">{get_score_status(docstring_coverage)[0]}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div style="background: rgba(255, 255, 255, 0.05); border-radius: 10px; padding: 15px; margin: 10px 0; border: 1px solid rgba(255, 255, 255, 0.1);">
                <p style="margin: 0; font-size: 0.9rem;"><strong>PEP-257 Compliance:</strong></p>
                <h4 style="margin: 5px 0;">{pep257_score:.1f}%</h4>
                <div class="{get_score_status(pep257_score)[1]}">{get_score_status(pep257_score)[0]}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Overall status message
        if overall_score >= 100:
            st.success("🎉 Excellent! Perfect scores in all categories!")
        elif overall_score >= 80:
            st.info(f"📊 Good overall score: {overall_score:.1f}%. Some improvements possible.")
        elif overall_score >= 60:
            st.warning(f"⚠️ Moderate overall score: {overall_score:.1f}%. Needs attention.")
        else:
            st.error(f"❌ Low overall score: {overall_score:.1f}%. Significant improvements needed.")
        
        # Additional stats
        st.markdown("---")
        st.markdown("### Additional Statistics")
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            comment_density = (counts['total_comments'] / max(data['metadata']['lines_of_code'], 1)) * 100
            st.metric("Comment Density", f"{comment_density:.1f}%")
        with col2:
            st.metric("Docstring Lines", counts['docstring_lines'])
        with col3:
            st.metric("Generators", total_generators)
        with col4:
            st.metric("Exceptions", total_exceptions)
        with col5:
            st.metric("PEP-257 Issues", pep257_summary.get('total_errors', 0))
        with col6:
            st.metric("Functions/Methods", counts['total_functions'] + counts['total_methods'])

    st.markdown('</div>', unsafe_allow_html=True)


def main():
    # Initialize session state for analysis
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    
    st.markdown("""
    <div class="glass-card" style="text-align: center;">
        <h1>Python Docstring Analyzer</h1>
        <p>Upload a Python file to analyze docstring coverage, comments, and generate baseline docstrings in multiple styles</p>
        <p>
            <small>⚡ Generator detection • ⚠️ Exception detection • 📋 PEP-257 compliance • ✅ Score Status</small>
        </p>
    </div>
    """, unsafe_allow_html=True)

    if not check_backend_connection():
        st.error("Backend server is not running.")
        st.code("cd backend\npython main.py")
        return
    
    # Upload section - only show if no analysis is in session
    if st.session_state.analysis_result is None:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Upload Python File")
        
        uploaded_file = st.file_uploader("Choose a .py file", type=["py"])
        
        if uploaded_file:
            st.success(f"File uploaded: {uploaded_file.name}")
            
            with st.expander("Preview Code"):
                st.code(uploaded_file.getvalue().decode("utf-8"), language="python")
            
            if st.button("Analyze Code, Comments & Docstrings", type="primary"):
                with st.spinner("Analyzing code structure, comments and docstrings..."):
                    uploaded_file.seek(0)
                    result = analyze_python_file(uploaded_file.read(), uploaded_file.name)
                    
                    if result:
                        # Store in session state
                        st.session_state.analysis_result = result
                        st.session_state.uploaded_file = uploaded_file
                        st.rerun()
        else:
            st.info("Please upload a Python (.py) file to begin analysis")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Info section
        st.markdown("""
        <div class="glass-card">
            <h4>How it works:</h4>
            <ol>
                <li>Upload a Python file (.py)</li>
                <li>The system analyzes all comments (both # and triple-quoted strings)</li>
                <li>Checks functions and methods for docstrings</li>
                <li><strong>Detects generator functions (yield statements) ⚡</strong></li>
                <li><strong>Detects exceptions raised (raise statements) ⚠️</strong></li>
                <li><strong>Checks PEP-257 compliance 📋</strong></li>
                <li><strong>Shows Passed/Failed status for scores ✅</strong></li>
                <li>View comment and docstring coverage statistics</li>
                <li>Generate docstrings in Google, NumPy, or reStructuredText styles</li>
                <li>Copy suggested docstrings to clipboard</li>
            </ol>
            <p><small>Features: • Parameter type detection • Return type analysis • Multiple docstring styles • Comment analysis • <strong>Generator detection • Exception detection • PEP-257 compliance • Score Status</strong></small></p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Display analysis results
        display_analysis_results(st.session_state.analysis_result)
        
        # Add a button to analyze another file
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        if st.button("Analyze Another File", type="primary"):
            st.session_state.analysis_result = None
            st.session_state.uploaded_file = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()