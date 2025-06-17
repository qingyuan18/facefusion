#!/usr/bin/env python3
"""
Uvicorn server startup script for FaceFusion API.

This script starts the FastAPI server using uvicorn with proper configuration.
"""

import os
import sys
import argparse
import uvicorn


def main():
    """Main function to start the server."""
    parser = argparse.ArgumentParser(description="Start FaceFusion API server")
    parser.add_argument(
        "--host", 
        default="0.0.0.0", 
        help="Host to bind the server to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="Port to bind the server to (default: 8000)"
    )
    parser.add_argument(
        "--reload", 
        action="store_true", 
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--workers", 
        type=int, 
        default=1, 
        help="Number of worker processes (default: 1)"
    )
    parser.add_argument(
        "--log-level", 
        default="info", 
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Log level (default: info)"
    )
    
    args = parser.parse_args()
    
    # Set environment variables
    os.environ['OMP_NUM_THREADS'] = '1'
    
    # Add current directory to Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    print(f"Starting FaceFusion API server...")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Workers: {args.workers}")
    print(f"Log level: {args.log_level}")
    print(f"Reload: {args.reload}")
    print(f"API Documentation: http://{args.host}:{args.port}/docs")
    print(f"Alternative docs: http://{args.host}:{args.port}/redoc")
    
    # Start the server
    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        workers=args.workers if not args.reload else 1,  # reload doesn't work with multiple workers
        reload=args.reload,
        log_level=args.log_level,
        access_log=True
    )


if __name__ == "__main__":
    main()
