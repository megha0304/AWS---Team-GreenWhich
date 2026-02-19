"""
FastAPI REST API for CloudForge Bug Intelligence.

Provides RESTful endpoints for workflow management, bug reports, and fix suggestions.
"""

from fastapi import FastAPI, HTTPException, status, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from typing import List, Optional, Literal
from datetime import datetime
import logging

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from cloudforge.api.models import (
    WorkflowCreateRequest,
    WorkflowResponse,
    WorkflowListResponse,
    ErrorResponse
)
from cloudforge.api.auth import verify_api_key
from cloudforge.models.state import AgentState, BugReport, FixSuggestion
from cloudforge.orchestration.state_store import StateStore
from cloudforge.orchestration.workflow_orchestrator import WorkflowOrchestrator
from cloudforge.utils.export import (
    export_bugs_to_json,
    export_bugs_to_csv,
    export_fixes_to_json,
    export_fixes_to_csv,
    export_workflow_summary_to_json
)


# Configure logging
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# Create FastAPI app
app = FastAPI(
    title="CloudForge Bug Intelligence API",
    description="AI-powered bug detection and resolution platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state (will be initialized on startup)
state_store: Optional[StateStore] = None
orchestrator: Optional[WorkflowOrchestrator] = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global state_store, orchestrator
    
    logger.info("Starting CloudForge Bug Intelligence API")
    
    # Initialize state store (placeholder - will be configured with real DynamoDB)
    state_store = StateStore(dynamodb_client=None, table_name="cloudforge-workflows")
    
    # Orchestrator will be initialized when needed
    logger.info("API startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down CloudForge Bug Intelligence API")


@app.get("/", tags=["Health"])
@limiter.limit("100/minute")
async def root(request: Request):
    """Root endpoint - API health check."""
    return {
        "service": "CloudForge Bug Intelligence API",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/health", tags=["Health"])
@limiter.limit("100/minute")
async def health_check(request: Request):
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.post(
    "/workflows",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Workflows"],
    responses={
        201: {"description": "Workflow created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"description": "Missing API key"},
        403: {"description": "Invalid API key"},
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
@limiter.limit("100/minute")
async def create_workflow(
    request: Request,
    workflow_request: WorkflowCreateRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Create a new bug detection workflow.
    
    This endpoint initiates a new workflow that will:
    1. Clone the repository
    2. Detect bugs using AI
    3. Generate test cases
    4. Execute tests
    5. Analyze results
    6. Generate fix suggestions
    
    The workflow runs asynchronously. Use the returned workflow_id to check status.
    """
    try:
        logger.info(
            f"Creating workflow for repository: {workflow_request.repository_url}",
            extra={"repository_url": workflow_request.repository_url, "branch": workflow_request.branch}
        )
        
        # For now, create a placeholder workflow
        # In production, this would trigger the orchestrator
        workflow_id = f"wf-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Create initial state
        initial_state = AgentState(
            workflow_id=workflow_id,
            repository_url=workflow_request.repository_url,
            repository_path=f"/tmp/repos/{workflow_id}",
            current_agent="initializing",
            status="pending",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Save to state store
        if state_store:
            await state_store.save_state(initial_state)
        
        # Return response
        return WorkflowResponse(
            workflow_id=workflow_id,
            status="pending",
            created_at=initial_state.created_at,
            updated_at=initial_state.updated_at,
            repository_url=workflow_request.repository_url,
            bugs_found=0,
            tests_generated=0,
            tests_executed=0,
            root_causes_found=0,
            fixes_generated=0
        )
        
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workflow: {str(e)}"
        )


@app.get(
    "/workflows/{workflow_id}",
    response_model=AgentState,
    tags=["Workflows"],
    responses={
        200: {"description": "Workflow found"},
        401: {"description": "Missing API key"},
        403: {"description": "Invalid API key"},
        404: {"model": ErrorResponse, "description": "Workflow not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
@limiter.limit("100/minute")
async def get_workflow(
    request: Request,
    workflow_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get workflow status and complete results.
    
    Returns the full workflow state including all bugs, tests, results,
    root causes, and fix suggestions.
    """
    try:
        logger.info(f"Fetching workflow: {workflow_id}")
        
        if not state_store:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="State store not initialized"
            )
        
        # Load workflow state
        workflow_state = await state_store.load_state(workflow_id)
        
        if not workflow_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        return workflow_state
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch workflow: {str(e)}"
        )


@app.get(
    "/workflows",
    response_model=WorkflowListResponse,
    tags=["Workflows"],
    responses={
        200: {"description": "Workflows retrieved successfully"},
        401: {"description": "Missing API key"},
        403: {"description": "Invalid API key"},
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
@limiter.limit("100/minute")
async def list_workflows(
    request: Request,
    status_filter: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    api_key: str = Depends(verify_api_key)
):
    """
    List workflows with optional filtering.
    
    Supports filtering by:
    - status: pending, in_progress, completed, failed
    - severity: critical, high, medium, low
    
    Results are paginated with configurable limit and offset.
    """
    try:
        logger.info(
            f"Listing workflows",
            extra={
                "status_filter": status_filter,
                "severity": severity,
                "limit": limit,
                "offset": offset
            }
        )
        
        if not state_store:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="State store not initialized"
            )
        
        # Build filters
        filters = {}
        if status_filter:
            filters["status"] = status_filter
        if severity:
            filters["severity"] = severity
        
        # Query workflows
        workflows = await state_store.query_workflows(filters)
        
        # Apply pagination
        total = len(workflows)
        paginated_workflows = workflows[offset:offset + limit]
        
        # Convert to response format
        workflow_responses = [
            WorkflowResponse(
                workflow_id=wf.workflow_id,
                status=wf.status,
                created_at=wf.created_at,
                updated_at=wf.updated_at,
                repository_url=wf.repository_url,
                bugs_found=len(wf.bugs),
                tests_generated=len(wf.test_cases),
                tests_executed=len(wf.test_results),
                root_causes_found=len(wf.root_causes),
                fixes_generated=len(wf.fix_suggestions)
            )
            for wf in paginated_workflows
        ]
        
        return WorkflowListResponse(
            workflows=workflow_responses,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workflows: {str(e)}"
        )


@app.get(
    "/workflows/{workflow_id}/bugs",
    response_model=List[BugReport],
    tags=["Bugs"],
    responses={
        200: {"description": "Bugs retrieved successfully"},
        401: {"description": "Missing API key"},
        403: {"description": "Invalid API key"},
        404: {"model": ErrorResponse, "description": "Workflow not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
@limiter.limit("100/minute")
async def get_bugs(
    request: Request,
    workflow_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get all bugs detected for a workflow.
    
    Returns a list of all bugs found during the bug detection phase,
    including severity, location, and code snippets.
    """
    try:
        logger.info(f"Fetching bugs for workflow: {workflow_id}")
        
        if not state_store:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="State store not initialized"
            )
        
        # Load workflow state
        workflow_state = await state_store.load_state(workflow_id)
        
        if not workflow_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        return workflow_state.bugs
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch bugs for workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch bugs: {str(e)}"
        )


@app.get(
    "/workflows/{workflow_id}/fixes",
    response_model=List[FixSuggestion],
    tags=["Fixes"],
    responses={
        200: {"description": "Fixes retrieved successfully"},
        401: {"description": "Missing API key"},
        403: {"description": "Invalid API key"},
        404: {"model": ErrorResponse, "description": "Workflow not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
@limiter.limit("100/minute")
async def get_fixes(
    request: Request,
    workflow_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get all fix suggestions for a workflow.
    
    Returns a list of all fix suggestions generated during the resolution phase,
    including code diffs, safety scores, and impact assessments.
    """
    try:
        logger.info(f"Fetching fixes for workflow: {workflow_id}")
        
        if not state_store:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="State store not initialized"
            )
        
        # Load workflow state
        workflow_state = await state_store.load_state(workflow_id)
        
        if not workflow_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        return workflow_state.fix_suggestions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch fixes for workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch fixes: {str(e)}"
        )


@app.get(
    "/workflows/{workflow_id}/bugs/export",
    tags=["Bugs"],
    responses={
        200: {"description": "Bugs exported successfully"},
        401: {"description": "Missing API key"},
        403: {"description": "Invalid API key"},
        404: {"model": ErrorResponse, "description": "Workflow not found"},
        400: {"model": ErrorResponse, "description": "Invalid export format"},
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
@limiter.limit("100/minute")
async def export_bugs(
    request: Request,
    workflow_id: str,
    format: Literal["json", "csv"] = "json",
    api_key: str = Depends(verify_api_key)
):
    """
    Export bug reports in JSON or CSV format.
    
    Supports two export formats:
    - json: Pretty-printed JSON with all bug details
    - csv: CSV format with bug fields (suitable for spreadsheet import)
    
    Returns the exported data with appropriate content type.
    """
    try:
        logger.info(f"Exporting bugs for workflow {workflow_id} in {format} format")
        
        if not state_store:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="State store not initialized"
            )
        
        # Load workflow state
        workflow_state = await state_store.load_state(workflow_id)
        
        if not workflow_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # Export based on format
        if format == "json":
            content = export_bugs_to_json(workflow_state.bugs, pretty=True)
            media_type = "application/json"
            filename = f"bugs_{workflow_id}.json"
        elif format == "csv":
            content = export_bugs_to_csv(workflow_state.bugs)
            media_type = "text/csv"
            filename = f"bugs_{workflow_id}.csv"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format: {format}. Must be 'json' or 'csv'"
            )
        
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export bugs for workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export bugs: {str(e)}"
        )


@app.get(
    "/workflows/{workflow_id}/fixes/export",
    tags=["Fixes"],
    responses={
        200: {"description": "Fixes exported successfully"},
        401: {"description": "Missing API key"},
        403: {"description": "Invalid API key"},
        404: {"model": ErrorResponse, "description": "Workflow not found"},
        400: {"model": ErrorResponse, "description": "Invalid export format"},
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
@limiter.limit("100/minute")
async def export_fixes(
    request: Request,
    workflow_id: str,
    format: Literal["json", "csv"] = "json",
    api_key: str = Depends(verify_api_key)
):
    """
    Export fix suggestions in JSON or CSV format.
    
    Supports two export formats:
    - json: Pretty-printed JSON with all fix details including code diffs
    - csv: CSV format with fix fields (suitable for spreadsheet import)
    
    Returns the exported data with appropriate content type.
    """
    try:
        logger.info(f"Exporting fixes for workflow {workflow_id} in {format} format")
        
        if not state_store:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="State store not initialized"
            )
        
        # Load workflow state
        workflow_state = await state_store.load_state(workflow_id)
        
        if not workflow_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # Export based on format
        if format == "json":
            content = export_fixes_to_json(workflow_state.fix_suggestions, pretty=True)
            media_type = "application/json"
            filename = f"fixes_{workflow_id}.json"
        elif format == "csv":
            content = export_fixes_to_csv(workflow_state.fix_suggestions)
            media_type = "text/csv"
            filename = f"fixes_{workflow_id}.csv"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format: {format}. Must be 'json' or 'csv'"
            )
        
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export fixes for workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export fixes: {str(e)}"
        )


@app.get(
    "/workflows/{workflow_id}/export",
    tags=["Workflows"],
    responses={
        200: {"description": "Workflow exported successfully"},
        401: {"description": "Missing API key"},
        403: {"description": "Invalid API key"},
        404: {"model": ErrorResponse, "description": "Workflow not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
@limiter.limit("100/minute")
async def export_workflow(
    request: Request,
    workflow_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Export complete workflow summary in JSON format.
    
    Returns a comprehensive JSON export containing:
    - Workflow metadata (ID, status, timestamps)
    - Summary statistics (counts of bugs, tests, fixes)
    - All bugs detected
    - All test cases generated
    - All test results
    - All root causes identified
    - All fix suggestions
    - All errors encountered
    
    This is useful for archiving complete workflow results or importing into
    external analysis tools.
    """
    try:
        logger.info(f"Exporting complete workflow {workflow_id}")
        
        if not state_store:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="State store not initialized"
            )
        
        # Load workflow state
        workflow_state = await state_store.load_state(workflow_id)
        
        if not workflow_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # Export complete workflow
        content = export_workflow_summary_to_json(workflow_state, pretty=True)
        
        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=workflow_{workflow_id}.json"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export workflow: {str(e)}"
        )


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={"error": "Not Found", "detail": str(exc.detail) if hasattr(exc, 'detail') else "Resource not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": "An unexpected error occurred"}
    )
