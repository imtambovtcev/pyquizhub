import uvicorn
from pyquizhub.adapters.web.web_adapter import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
