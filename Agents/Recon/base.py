class SubAgent:
    def __init__(self, llm):
        self.llm = llm

    async def execute(self, target: str) -> dict:
        raise NotImplementedError("Each agent must implement execute()")