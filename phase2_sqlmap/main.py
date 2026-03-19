import asyncio
from graph import build_graph
from langchain_ollama import ChatOllama


async def main():
    llm = ChatOllama(model="llama3.2:latest")
    
    print("=" * 60)
    print("SQLMap Agent - Autonomous SQL Injection Testing")
    print("=" * 60)
    
    graph = build_graph(llm, mode="sqlmap")
    
    initial_state = {
        "docker_status": "OFF",
        "target": "dvwa",
        "command": None,
        "docker_result": None,
        "message": None,
        "web_targets": [],
        "sqlmap_commands": [],
        "sqlmap_results": [],
        "neo4j_data": {}
    }

    print("\n[1] Starting Docker check...")
    print("[2] Fetching recon data from Neo4j...")
    print("[3] Generating SQLMap commands with LLM...")
    print("[4] Executing SQLMap in Kali container...")
    print("[5] Storing results in Neo4j...\n")
    
    result = await graph.ainvoke(initial_state)

    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    
    print(f"\nWeb Targets Found: {len(result.get('web_targets', []))}")
    for target in result.get('web_targets', []):
        print(f"  - {target.get('url')}")
    
    print(f"\nSQLMap Commands Generated: {len(result.get('sqlmap_commands', []))}")
    for cmd in result.get('sqlmap_commands', []):
        print(f"  - {cmd[:80]}...")
    
    print(f"\nSQLMap Results: {len(result.get('sqlmap_results', []))}")
    for res in result.get('sqlmap_results', []):
        vuln = res.get('vulnerability_found', False)
        status = "VULNERABLE" if vuln else "NOT VULNERABLE"
        print(f"  - {status}")
        if vuln:
            print(f"    Parameter: {res.get('vulnerable_parameter')}")
            print(f"    DB Type: {res.get('database_type')}")
    
    print(f"\nMessage: {result.get('message')}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
