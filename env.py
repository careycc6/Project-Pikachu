class ShowdownEnv:
    def reset(self, seed=None):
        return {"message": "battle started"}
    def step(self, action_id):
        return {"message": "step taken"}, 0.0, False
