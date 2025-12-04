"""FastAPI web server for Cluster Inventory Service."""

import os
import logging
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import modules from the same directory (using importlib since directory has hyphen)
import importlib.util
import os

def _import_module(name, path):
    """Import a module from a file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

_base_dir = os.path.dirname(__file__)
_cluster_manager = _import_module("cluster_manager", os.path.join(_base_dir, "cluster_manager.py"))
_cluster_registry = _import_module("cluster_registry", os.path.join(_base_dir, "cluster_registry.py"))
_cluster_discovery = _import_module("cluster_discovery", os.path.join(_base_dir, "cluster_discovery.py"))
_security_scan_storage = _import_module("security_scan_storage", os.path.join(_base_dir, "security_scan_storage.py"))

ClusterManager = _cluster_manager.ClusterManager
ClusterRegistry = _cluster_registry.ClusterRegistry
discover_and_register_cluster = _cluster_discovery.discover_and_register_cluster
SecurityScanStorage = _security_scan_storage.SecurityScanStorage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
APP_NAME = os.getenv("APP_NAME", "cluster-inventory")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8001"))

# Initialize FastAPI app
app = FastAPI(
    title="Cluster Inventory API",
    description="Kubernetes Cluster Inventory Management Service",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global cluster management instances
cluster_manager: Optional[ClusterManager] = None
cluster_registry: Optional[ClusterRegistry] = None
security_scan_storage: Optional[SecurityScanStorage] = None


# Request/Response models
class ClusterCreateRequest(BaseModel):
    name: str
    kubeconfig: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class ClusterUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    kubeconfig: Optional[str] = None


class ClusterResponse(BaseModel):
    id: str
    name: str
    description: str
    tags: List[str]
    status: str
    created_at: str
    updated_at: str
    last_checked: Optional[str] = None
    has_kubeconfig: bool


class HealthResponse(BaseModel):
    status: str
    service: str
    ready: bool


@app.on_event("startup")
async def startup_event():
    """Initialize cluster management on startup."""
    global cluster_manager, cluster_registry, security_scan_storage
    
    logger.info("Initializing Cluster Inventory Service...")
    
    try:
        # Initialize cluster management
        cluster_manager = ClusterManager()
        cluster_registry = ClusterRegistry()
        security_scan_storage = SecurityScanStorage()
        logger.info("Cluster management initialized")
        
        # Auto-discover and register in-cluster configuration
        try:
            discovered_cluster_id = discover_and_register_cluster(cluster_registry)
            if discovered_cluster_id:
                logger.info(f"In-cluster configuration auto-registered: {discovered_cluster_id}")
            else:
                logger.debug("No in-cluster configuration to auto-register")
        except Exception as e:
            logger.warning(f"Failed to auto-discover in-cluster configuration: {e}")
        
        logger.info("Cluster Inventory Service initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize cluster inventory service: {e}", exc_info=True)
        raise


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="cluster-inventory",
        ready=cluster_registry is not None and cluster_manager is not None,
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Cluster Inventory",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "clusters": "/clusters",
            "docs": "/docs",
        },
    }


@app.post("/clusters", response_model=ClusterResponse)
async def create_cluster(request: ClusterCreateRequest):
    """Register a new Kubernetes cluster."""
    if not cluster_registry:
        raise HTTPException(status_code=503, detail="Cluster management not initialized")
    
    # Validate kubeconfig
    validation = cluster_manager.validate_kubeconfig(request.kubeconfig)
    if not validation.get("valid"):
        raise HTTPException(status_code=400, detail=f"Invalid kubeconfig: {validation.get('error')}")
    
    # Register cluster
    cluster_id = cluster_registry.register_cluster(
        name=request.name,
        kubeconfig=request.kubeconfig,
        description=request.description,
        tags=request.tags or []
    )
    
    if not cluster_id:
        raise HTTPException(status_code=500, detail="Failed to register cluster")
    
    # Get cluster info
    cluster = cluster_registry.get_cluster(cluster_id)
    if not cluster:
        raise HTTPException(status_code=500, detail="Cluster registered but not found")
    
    return ClusterResponse(**cluster)


@app.get("/clusters", response_model=List[ClusterResponse])
async def list_clusters():
    """List all registered clusters."""
    if not cluster_registry:
        raise HTTPException(status_code=503, detail="Cluster management not initialized")
    
    clusters = cluster_registry.list_clusters()
    return [ClusterResponse(**cluster) for cluster in clusters]


@app.get("/clusters/{cluster_id}", response_model=ClusterResponse)
async def get_cluster(cluster_id: str):
    """Get cluster details."""
    if not cluster_registry:
        raise HTTPException(status_code=503, detail="Cluster management not initialized")
    
    cluster = cluster_registry.get_cluster(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    return ClusterResponse(**cluster)


@app.put("/clusters/{cluster_id}", response_model=ClusterResponse)
async def update_cluster(cluster_id: str, request: ClusterUpdateRequest):
    """Update cluster information."""
    if not cluster_registry:
        raise HTTPException(status_code=503, detail="Cluster management not initialized")
    
    # Validate kubeconfig if provided
    if request.kubeconfig:
        validation = cluster_manager.validate_kubeconfig(request.kubeconfig)
        if not validation.get("valid"):
            raise HTTPException(status_code=400, detail=f"Invalid kubeconfig: {validation.get('error')}")
    
    # Update cluster
    success = cluster_registry.update_cluster(
        cluster_id=cluster_id,
        name=request.name,
        description=request.description,
        tags=request.tags,
        kubeconfig=request.kubeconfig
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update cluster")
    
    # Get updated cluster info
    cluster = cluster_registry.get_cluster(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found after update")
    
    return ClusterResponse(**cluster)


@app.delete("/clusters/{cluster_id}")
async def delete_cluster(cluster_id: str):
    """Delete a cluster."""
    if not cluster_registry:
        raise HTTPException(status_code=503, detail="Cluster management not initialized")
    
    success = cluster_registry.delete_cluster(cluster_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete cluster")
    
    return {"message": "Cluster deleted successfully", "cluster_id": cluster_id}


@app.post("/clusters/{cluster_id}/test")
async def test_cluster_connection(cluster_id: str):
    """Test connection to a cluster."""
    if not cluster_manager:
        raise HTTPException(status_code=503, detail="Cluster management not initialized")
    
    result = cluster_manager.test_connection(cluster_id)
    return result


@app.get("/clusters/{cluster_id}/info")
async def get_cluster_info(cluster_id: str):
    """Get detailed cluster information including connection status."""
    if not cluster_manager:
        raise HTTPException(status_code=503, detail="Cluster management not initialized")
    
    info = cluster_manager.get_cluster_info(cluster_id)
    if not info:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    return info


@app.get("/clusters/{cluster_id}/kubeconfig")
async def get_cluster_kubeconfig(cluster_id: str):
    """Get kubeconfig for a cluster."""
    if not cluster_registry:
        raise HTTPException(status_code=503, detail="Cluster management not initialized")
    
    from .storage import ClusterStorage
    storage = ClusterStorage()
    kubeconfig = storage.get_kubeconfig(cluster_id)
    
    if not kubeconfig:
        raise HTTPException(status_code=404, detail="Kubeconfig not found")
    
    return {"cluster_id": cluster_id, "kubeconfig": kubeconfig}


@app.post("/clusters/discover")
async def discover_in_cluster():
    """Manually trigger discovery and registration of in-cluster configuration."""
    if not cluster_registry:
        raise HTTPException(status_code=503, detail="Cluster management not initialized")
    
    try:
        cluster_id = discover_and_register_cluster(cluster_registry, force=False)
        if cluster_id:
            cluster = cluster_registry.get_cluster(cluster_id)
            return {
                "message": "In-cluster configuration discovered and registered",
                "cluster_id": cluster_id,
                "cluster": cluster
            }
        else:
            return {
                "message": "Not running in-cluster or cluster already registered",
                "cluster_id": None
            }
    except Exception as e:
        logger.error(f"Error during cluster discovery: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")


# Security scan storage endpoints
class SecurityScanSaveRequest(BaseModel):
    scan_id: str
    result: Dict[str, Any]


@app.post("/security/scans/{cluster_id}")
async def save_security_scan(cluster_id: str, request: SecurityScanSaveRequest):
    """Save a security scan result for a cluster."""
    if not security_scan_storage:
        raise HTTPException(status_code=503, detail="Security scan storage not initialized")
    
    try:
        success = security_scan_storage.save_scan_result(
            cluster_id=cluster_id,
            scan_id=request.scan_id,
            result=request.result
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save scan result")
        return {"message": "Scan result saved", "cluster_id": cluster_id, "scan_id": request.scan_id}
    except Exception as e:
        logger.error(f"Error saving scan result: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save scan result: {str(e)}")


@app.get("/security/scans/{cluster_id}")
async def get_security_scans(cluster_id: str, limit: Optional[int] = None):
    """Get security scan results for a cluster."""
    if not security_scan_storage:
        raise HTTPException(status_code=503, detail="Security scan storage not initialized")
    
    try:
        results = security_scan_storage.get_scan_results(cluster_id, limit=limit)
        return results
    except Exception as e:
        logger.error(f"Error retrieving scan results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve scan results: {str(e)}")


@app.get("/security/scans/{cluster_id}/latest")
async def get_latest_security_scan(cluster_id: str):
    """Get the latest security scan result for a cluster."""
    if not security_scan_storage:
        raise HTTPException(status_code=503, detail="Security scan storage not initialized")
    
    try:
        result = security_scan_storage.get_latest_scan_result(cluster_id)
        if not result:
            raise HTTPException(status_code=404, detail="No scan results found for this cluster")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving latest scan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve latest scan: {str(e)}")

