from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class StepRequest(BaseModel):
    action: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/reset")
def reset():
    return {"observation": {"message": "battle started"}, "done": False}

@app.post("/step")
def step(req: StepRequest):
    return {"observation": {"message": "step"}, "reward": 0.0, "done": False}

@app.post("/close")
def close():
    return {"status": "closed"}
