from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from analyzer import analyze_python_code
import logging

# -------------------------------------------------------------------
# Logging setup
# -------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# FastAPI app setup
# -------------------------------------------------------------------
app = FastAPI(
    title="Python Docstring Generator API",
    description="Analyzes Python code structure and generates docstrings",
    version="1.0.0",
)

# -------------------------------------------------------------------
# CORS configuration (for Streamlit frontend)
# -------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "active",
        "message": "Python Code Analyzer API is running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/analyze")
async def analyze_code(file: UploadFile = File(...)):
    """
    Analyze Python code from an uploaded file.

    Args:
        file: Python file to analyze (.py extension expected)

    Returns:
        Dictionary with analysis results
    """
    try:
        # Validate file extension
        if not file.filename.endswith(".py"):
            raise HTTPException(
                status_code=400,
                detail="Only Python (.py) files are supported",
            )

        # Read file content
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty",
            )

        # Decode content
        try:
            source_code = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="File must be UTF-8 encoded",
            )

        # Log basic file info (no source code for privacy)
        logger.info(
            f"Analyzing file: {file.filename}, "
            f"Size: {len(source_code)} chars"
        )

        # Analyze code
        try:
            analysis_result = analyze_python_code(source_code)
        except SyntaxError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid Python syntax: {str(e)}",
            )

        return {
            "filename": file.filename,
            "analysis": analysis_result,
            "metadata": {
                "file_size_bytes": len(content),
                "lines_of_code": len(source_code.splitlines()),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}",
        )


# -------------------------------------------------------------------
# Entrypoint
# -------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
