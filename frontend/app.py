# frontend/app.py
import streamlit as st
import requests
from typing import Dict, Optional, List

# Page configuration
st.set_page_config(
    page_title="Python Docstring Generator",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
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
</style>
""", unsafe_allow_html=True)

BACKEND_URL = "http://localhost:8000"


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


def display_docstring_analysis(counts: Dict):
    """Display docstring statistics and analysis."""
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("📝 Docstring Analysis")
    
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
            emoji = "✅"
        elif coverage >= 50:
            delta_color = "off"
            emoji = "⚠️"
        else:
            delta_color = "inverse"
            emoji = "❌"
        
        st.metric(
            "Coverage Percentage",
            f"{coverage:.1f}%",
            delta=emoji,
            delta_color=delta_color
        )
    
    st.markdown('</div>', unsafe_allow_html=True)


def display_comment_analysis(counts: Dict):
    """Display comment statistics."""
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("💬 Comment Analysis")
    
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


def display_function_details(function_details: List[Dict], title: str, is_method: bool = False):
    """Display detailed information about functions or methods."""
    if not function_details:
        return
    
    st.markdown(f"### {title}")
    
    for func in function_details:
        with st.expander(f"{func['class_name'] + '.' if is_method else ''}{func['name']}"):
            col1, col2 = st.columns([1, 3])
            
            with col1:
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
            
            with col2:
                if func['has_docstring'] and func['docstring']:
                    st.markdown("**Current Docstring:**")
                    st.code(func['docstring'], language='python')
                else:
                    st.markdown("**Baseline Docstring:**")
                    st.markdown(f'<div class="baseline-docstring">{func["baseline_docstring"]}</div>', unsafe_allow_html=True)
                    
                    # Add copy to clipboard button for baseline docstring
                    if st.button(f"📋 Copy Baseline", key=f"copy_{func['name']}_{func.get('class_name', '')}"):
                        st.code(func['baseline_docstring'], language='python')
                        st.success("Copied to clipboard!")


def display_analysis_results(data: Dict):
    analysis = data["analysis"]
    counts = analysis["counts"]

    st.markdown('<h1 class="main-header">📊 Analysis Results</h1>', unsafe_allow_html=True)

    # Basic metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Modules", counts["total_modules"])
    col2.metric("Classes", counts["total_classes"])
    col3.metric("Functions", counts["total_functions"])
    col4.metric("Methods", counts["total_methods"])
    col5.metric("Lines of Code", data['metadata']['lines_of_code'])

    # Comment analysis section
    display_comment_analysis(counts)
    
    # Docstring analysis section
    display_docstring_analysis(counts)

    # Detailed breakdown with tabs
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("📝 Detailed Breakdown")
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["Functions", "Methods", "Docstrings", "File Info"])

    with tab1:
        if analysis["function_details"]:
            display_function_details(analysis["function_details"], "Top-level Functions")
        else:
            st.info("No top-level functions found.")

    with tab2:
        if analysis["method_details"]:
            display_function_details(analysis["method_details"], "Class Methods", is_method=True)
        else:
            st.info("No methods found.")

    with tab3:
        st.markdown("### 📋 Docstring Summary")
        
        # Functions with missing docstrings
        missing_functions = [f for f in analysis["function_details"] if not f['has_docstring']]
        missing_methods = [m for m in analysis["method_details"] if not m['has_docstring']]
        
        if missing_functions or missing_methods:
            st.warning(f"Found {len(missing_functions)} functions and {len(missing_methods)} methods without docstrings")
            
            if missing_functions:
                st.markdown("**Functions needing docstrings:**")
                for func in missing_functions:
                    st.markdown(f"- `{func['name']}()`")
            
            if missing_methods:
                st.markdown("**Methods needing docstrings:**")
                for method in missing_methods:
                    st.markdown(f"- `{method['class_name']}.{method['name']}()`")
        else:
            st.success("🎉 All functions and methods have docstrings!")
        
        # Show coverage progress
        if counts['total_functions'] + counts['total_methods'] > 0:
            coverage = counts.get('docstring_coverage', 0)
            st.progress(coverage / 100)
            st.caption(f"Overall docstring coverage: {coverage:.1f}%")

    with tab4:
        st.subheader("📄 File Information")
        col1, col2, col3 = st.columns(3)
        col1.write(f"**Filename:** {data['filename']}")
        col2.write(f"**Size:** {data['metadata']['file_size_bytes']} bytes")
        col3.write(f"**Lines of Code:** {data['metadata']['lines_of_code']}")
        
        # Additional stats
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            comment_density = (counts['total_comments'] / max(data['metadata']['lines_of_code'], 1)) * 100
            st.metric("Comment Density", f"{comment_density:.1f}%")
        with col2:
            st.metric("Docstring Lines", counts['docstring_lines'])
        with col3:
            st.metric("Total Elements", counts['total_functions'] + counts['total_methods'] + counts['total_classes'])

    st.markdown('</div>', unsafe_allow_html=True)


def main():
    st.markdown("""
    <div class="glass-card" style="text-align: center;">
        <h1> Python Docstring Analyzer</h1>
        <p>Upload a Python file to analyze docstring coverage, comments, and generate baseline docstrings</p>
    </div>
    """, unsafe_allow_html=True)

    if not check_backend_connection():
        st.error("Backend server is not running.")
        st.code("cd backend\npython main.py")
        return

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("📤 Upload Python File")

    uploaded_file = st.file_uploader("Choose a .py file", type=["py"])

    if uploaded_file:
        st.success(f"✅ File uploaded: {uploaded_file.name}")

        with st.expander("📋 Preview Code"):
            st.code(uploaded_file.getvalue().decode("utf-8"), language="python")

        if st.button("🔍 Analyze Code, Comments & Docstrings", type="primary"):
            with st.spinner("Analyzing code structure, comments and docstrings..."):
                uploaded_file.seek(0)
                result = analyze_python_file(uploaded_file.read(), uploaded_file.name)

                if result:
                    display_analysis_results(result)
                    st.success("✅ Analysis completed successfully!")
                    

    else:
        st.info("👆 Please upload a Python (.py) file to begin analysis")

    st.markdown('</div>', unsafe_allow_html=True)

    # Info section
    st.markdown("""
    <div class="glass-card">
        <h4>💡 How it works:</h4>
        <ol>
            <li>Upload a Python file (.py)</li>
            <li>The system analyzes all comments (both # and triple-quoted strings)</li>
            <li>Checks functions and methods for docstrings</li>
            <li>View comment and docstring coverage statistics</li>
            <li>See baseline docstrings for functions without documentation</li>
            <li>Copy suggested docstrings to clipboard</li>
        </ol>
        <p><small>Features: • Parameter type detection • Return type analysis • Google-style docstring generation • Comment analysis</small></p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()