#!/usr/bin/env python
import uvicorn
from uvicorn_config import host, port, reload, workers, log_level

if __name__ == "__main__":
    print(f"Starting FastAPI application on http://{host}:{port}")
    print(f"API documentation available at http://{host}:{port}/docs")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level=log_level
    )
