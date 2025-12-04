"""Scheduled security scan runner for CronJob."""

import os
import sys
import logging
from backend.services.sreagent.security_scanner import SecurityScanner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Run security scan for all clusters."""
    logger.info("Starting scheduled security scan for all clusters")
    
    try:
        scanner = SecurityScanner()
        
        # Get namespaces from environment (optional)
        namespaces = None
        if os.getenv("SCAN_NAMESPACES"):
            namespaces = os.getenv("SCAN_NAMESPACES").split(",")
        
        # Scan all clusters
        results = scanner.scan_all_clusters(namespaces=namespaces)
        
        logger.info(f"Security scan completed. Scanned {len(results)} clusters.")
        
        # Log results
        for result in results:
            if result.get("status") == "completed":
                logger.info(f"Cluster {result.get('cluster_id')}: Scan completed successfully")
            else:
                logger.error(f"Cluster {result.get('cluster_id')}: Scan failed - {result.get('error')}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Security scan failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

