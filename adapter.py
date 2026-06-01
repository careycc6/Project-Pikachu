from fastapi import FastAPI
from pydantic import BaseModel
from env import ShowdownEnv

app = FastAPI()
env = ShowdownEnv()

class StepRequest(BaseModel):
    action: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/reset")
def reset():
    obs = env.reset()
    return {"observation": obs, "done": False}

@app.post("/step")
def step(req: StepRequest):
    obs, reward, done = env.step(req.action)
    return {"observation": obs, "reward": reward, "done": done}

@app.post("/close")
def close():
    return {"status": "closed"}
