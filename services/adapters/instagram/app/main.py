from fastapi import FastAPI

app = FastAPI(title="Instagram Adapter", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Instagram Adapter", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
