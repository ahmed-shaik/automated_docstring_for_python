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
    description="Analyzes Python code structure and generates docstrings with PEP-257 compliance checking",
    version="2.0.0",
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
        "version": "2.0.0",
        "features": [
            "AST Analysis",
            "Docstring Generation (Google/NumPy/reST)",
            "Comment Analysis",
            "PEP-257 Compliance Checking",
            "Generator Detection",
            "Exception Detection",
            "Quality Gate Support"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "checker": "PEP257Checker integrated"}


@app.post("/analyze")
async def analyze_code(
    file: UploadFile = File(...), 
    require_all_magic_methods: bool = False,
    min_pep257_score: float = None
):
    """
    Analyze Python code from an uploaded file.

    Args:
        file: Python file to analyze (.py extension expected)
        require_all_magic_methods: If True, require docstrings for all magic methods
        min_pep257_score: Optional minimum PEP-257 score (0-100) for quality gate.
                          If provided and score is below this, analysis will indicate failure.

    Returns:
        Dictionary with analysis results including PEP-257 compliance score
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
            f"Size: {len(source_code)} chars, "
            f"Require all magic methods: {require_all_magic_methods}, "
            f"Min PEP257 score: {min_pep257_score}"
        )

        # Analyze code
        try:
            analysis_result = analyze_python_code(source_code, require_all_magic_methods)
        except SyntaxError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid Python syntax: {str(e)}",
            )

        # Check quality gate if min_pep257_score is provided
        quality_gate_passed = None
        quality_gate_message = None

        if min_pep257_score is not None:
            pep257_score = analysis_result.get("pep257_analysis", {}).get("summary", {}).get("pep257_compliance_score", 0)
            quality_gate_passed = pep257_score >= min_pep257_score

            if quality_gate_passed:
                quality_gate_message = f"Quality gate passed: {pep257_score}% >= {min_pep257_score}%"
                logger.info(f"Quality gate passed for {file.filename}: {pep257_score}% >= {min_pep257_score}%")
            else:
                quality_gate_message = f"Quality gate failed: {pep257_score}% < {min_pep257_score}%"
                logger.warning(f"Quality gate failed for {file.filename}: {pep257_score}% < {min_pep257_score}%")

        response = {
            "filename": file.filename,
            "analysis": analysis_result,
            "metadata": {
                "file_size_bytes": len(content),
                "lines_of_code": len(source_code.splitlines()),
                "require_all_magic_methods": require_all_magic_methods
            },
        }

        # Add quality gate info if it was checked
        if min_pep257_score is not None:
            response["quality_gate"] = {
                "min_score": min_pep257_score,
                "actual_score": analysis_result.get("pep257_analysis", {}).get("summary", {}).get("pep257_compliance_score", 0),
                "passed": quality_gate_passed,
                "message": quality_gate_message
            }

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}",
        )


@app.post("/analyze-with-quality-gate")
async def analyze_with_quality_gate(
    file: UploadFile = File(...),
    min_score: float = 80.0
):
    """
    Analyze code with strict quality gate enforcement.

    This endpoint will return a 400 error if the PEP-257 score is below min_score.
    Useful for CI/CD pipelines.

    Args:
        file: Python file to analyze
        min_score: Minimum required PEP-257 score (default: 80.0)

    Returns:
        Analysis results or HTTP 400 if quality gate fails
    """
    try:
        if not file.filename.endswith(".py"):
            raise HTTPException(status_code=400, detail="Only Python (.py) files are supported")

        content = await file.read()
        source_code = content.decode("utf-8")

        analysis_result = analyze_python_code(source_code)
        pep257_score = analysis_result.get("pep257_analysis", {}).get("summary", {}).get("pep257_compliance_score", 0)

        if pep257_score < min_score:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": f"PEP-257 quality gate failed: {pep257_score}% < {min_score}%",
                    "score": pep257_score,
                    "required": min_score,
                    "violations": analysis_result.get("pep257_analysis", {}).get("errors", [])
                }
            )

        return {
            "filename": file.filename,
            "analysis": analysis_result,
            "quality_gate": {
                "passed": True,
                "score": pep257_score,
                "required": min_score
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quality gate analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# -------------------------------------------------------------------
# Entrypoint
# -------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
