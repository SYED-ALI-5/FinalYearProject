import asyncio
from graph import build_graph
from langchain_ollama import ChatOllama



async def main():
    llm = ChatOllama(model="deepseek-llm:7b")
    graph = build_graph(llm)

    initial_state = {
        "docker_status": "OFF",
        "target": "cuonline.cuilahore.edu.pk",
        "command": None,
        "docker_result": None,
        "message": None
    }


    result = await graph.ainvoke(initial_state)

    print(result)

asyncio.run(main())
