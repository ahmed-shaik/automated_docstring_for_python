# Python Docstring Analyzer & Generator

A full-stack Python application that analyzes Python source code to extract structural details (modules, classes, functions, and methods), evaluates comment and docstring coverage, and generates baseline Google-style docstrings for undocumented functions.

The project follows a clean **client–server architecture**, using **FastAPI** as the backend for code analysis and **Streamlit** as the frontend for visualization.

---

## Features

- Upload Python (`.py`) files for analysis
- Detect:
  - Modules
  - Classes
  - Top-level functions
  - Class methods
- Comment analysis:
  - Single-line comments (`#`)
  - Multi-line comments (triple-quoted strings)
- Docstring analysis:
  - Identify missing and existing docstrings
  - Compute docstring coverage percentage
- Baseline docstring generation (Google-style)
- Side-by-side visualization of code structure and documentation status
- In-memory file processing (no files stored on disk)
- REST API backend using FastAPI
- Interactive frontend using Streamlit

---

## Project Architecture

python-docstring-generator/
│
├── backend/
│ ├── main.py # FastAPI backend (API endpoints)
│ ├── analyzer.py # AST-based analysis & docstring logic
│
├── frontend/
│ ├── app.py # Streamlit frontend UI
│
├── requirements.txt
└── README.md

### Architecture Overview

- **Frontend (Streamlit)**  
  Handles file upload, visualization, and user interaction.

- **Backend (FastAPI)**  
  Exposes REST APIs to analyze Python source code.

- **Analyzer Module**  
  Uses Python’s built-in `ast` module for static code analysis without executing the code.

---

## Technologies Used

- Python 3.9+
- FastAPI
- Streamlit
- Uvicorn
- Python AST (Abstract Syntax Tree)
- Requests

---

## Setup and Installation

### 1. Clone the repository

```bash
git https://github.com/ahmed-shaik/automated_docstring_for_python.git
cd automated_docstring_for_python
```

### Architecture Overview

- **Frontend (Streamlit)**  
  Handles file upload, visualization, and user interaction.

- **Backend (FastAPI)**  
  Exposes REST APIs to analyze Python source code.

- **Analyzer Module**  
  Uses Python’s built-in `ast` module for static code analysis without executing the code.

---

## Technologies Used

- Python 3.9+
- FastAPI
- Streamlit
- Uvicorn
- Python AST (Abstract Syntax Tree)
- Requests

---

## Setup and Installation

### 1. Clone the repository

```bash
git clone https://github.com/ahmed-shaik/automated_docstring_for_python.git
cd automated_docstring_for_python
2. Create and activate a virtual environment
Windows
python -m venv venv
venv\Scripts\activate

macOS / Linux
python3 -m venv venv
source venv/bin/activate

3. Install dependencies
pip install -r requirements.txt

Running the Application
Step 1: Start the FastAPI backend
uvicorn backend.main:app --reload


Backend will run at:

http://localhost:8000


API documentation (Swagger UI):

http://localhost:8000/docs

Step 2: Start the Streamlit frontend

Open a new terminal (with the virtual environment activated):

streamlit run frontend/app.py


Frontend will run at:

http://localhost:8501

How It Works

The user uploads a Python .py file via the Streamlit UI.

The file is sent in memory to the FastAPI backend.

The backend parses the source code using Python AST.

Structural, comment, and docstring analysis is performed.

Results are returned as structured JSON.

Streamlit displays:

Code metrics

Comment analysis

Docstring coverage

Baseline docstring suggestions

Note: Uploaded files are never saved to disk.

Example Use Cases

Improving documentation quality in Python projects

Identifying undocumented functions and methods

Learning Python AST and static code analysis

Code quality analysis for academic or industry projects

Future Enhancements

Download modified code with generated docstrings

Support for NumPy and reStructuredText docstring styles

Multi-file and folder-level analysis

Integration with GitHub repositories

AI-assisted docstring refinement

Author

Ahmed
B.Tech – Computer Science and Machine Learning
Final Year Project
Infosys Springboard Program

License

This project is intended for academic and learning purposes.
You are free to fork and modify it with proper attribution.
```
