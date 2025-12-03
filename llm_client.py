from typing import Dict
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
import subprocess
from langchain_ollama import ChatOllama
import re



llm = ChatOllama(model="deepseek-llm:7b")


class AgentState(TypedDict):
    docker_image: str = "OFF"
    website: str = ""
    message: str = ""

def run_shell_command(command: str | list) -> str:
    try:
        result = subprocess.check_output(
            command,
            cwd="../FinalYearProject/docker",
            text=True,
            stderr=subprocess.STDOUT
        )
        return result
    except subprocess.CalledProcessError as e:
        return e.output
    
def run_docker_compose():
    try:
        result = subprocess.check_output(
            ["docker", "compose", "up", "-d"],
            cwd="../FinalYearProject/docker",
            text=True,
            stderr=subprocess.STDOUT
        )
        return result
    except subprocess.CalledProcessError as e:
        return e.output

SAFE_COMMANDS = {
        "is_docker_running": "docker info",
        "list_containers": "docker ps",
        "list_images": "docker images",
        "is_container_running": "docker ps --filter name=<container_name>",
        "check_image": "docker images | grep <image_name>",
    }

workflow = StateGraph(AgentState)

def docker_agent(state: AgentState):
    docker_image_status = state.get("docker_image", "OFF")

    if docker_image_status == "OFF":
        return {
            "docker_image": "OFF",
            "website": state.get("website", ""),
            "message": "Docker image is turned OFF. No action taken.",
            "__end__": True
        }

    output = run_docker_compose()

    return {
        "docker_image": "ON",
        "website": state.get("website", ""),
        "message": output,
    }

    ## todo: checking the initial status of docker image
def llm_agent(state: AgentState):
    user_input = input("Enter website URL: ").strip()
    # response = llm.invoke(user_input)
    # text = response.content.strip()

    # extracting URL from user input
    found_urls = re.findall(r'(https?://\S+|http://\S+)', user_input)
    if found_urls:
        return {
            "docker_image": state.get("docker_image", "OFF"),
            "website": found_urls[0],
            "message": f"Got website: {found_urls[0]}"
        }

    # No URL → keep asking
    return {
        "docker_image": state.get("docker_image", "OFF"),
        "website": "",
        "message": "No valid URL found in input. Please provide a valid website URL."
    }

def website_agent(state: AgentState):
    website = state.get("website", "")
    if not website:
        return {
            "docker_image": state["docker_image"],
            "website": "",
            "message": "No website provided.",
            "__end__": True
        }

    # command = f"curl -I {website}"
    # output = run_shell_command(command)

    return {
        "docker_image": state["docker_image"],
        "website": website,
        "message": "Url provided"
    }
    

# def sqlmap_agent(state: AgentState):
#     website = state.get("website", "")
#     if not website:
#         return {
#             "docker_image": state["docker_image"],
#             "website": "",
#             "message": "No website provided for SQLMap scan.",
#             "__end__": True
#         }
#     run_shell_command("docker exec -it kali /bin/bash")
#     # todo: add LLM to generate sqlmap command based on website 
#     command = f"/root/scripts/run_allowed.sh sqlmap -u \"{website}/vulnerabilities/sqli/?id=1&Submit=Submit\" --cookie=\"PHPSESSID=jqfr7435v2lml5a54ip1jgmco7; security=low\""
#     output = run_shell_command(command)

#     return {
#         "docker_image": state["docker_image"],
#         "website": website,
#         "message": output
#     }

def sqlmap_agent(state: AgentState):
    website = state.get("website", "")
    if not website:
        return {
            "docker_image": state["docker_image"],
            "website": "",
            "message": "No website provided for SQLMap scan.",
            "__end__": True
        }


    command = [
        "docker", "exec", "kali",
        "/root/scripts/run_allowed.sh",
        "sqlmap",
        "-u", f"{website}/vulnerabilities/sqli/?id=1&Submit=Submit",
        "--cookie", "PHPSESSID=jqfr7435v2lml5a54ip1jgmco7; security=low"
    ]

    output = run_shell_command(command)

    return {
        "docker_image": state["docker_image"],
        "website": website,
        "message": output
    }



workflow.add_node(
    "Docker Agent",
    docker_agent,
)
workflow.add_node(
    "LLM Agent",
    llm_agent,
)
workflow.add_node(
    "Website Agent",
    website_agent,
)
workflow.add_node(
    "SQLMap Agent",
    sqlmap_agent,
)
workflow.set_entry_point("Docker Agent")
workflow.add_edge("Docker Agent", "LLM Agent")
workflow.add_edge("LLM Agent", "Website Agent")
workflow.add_edge("Website Agent", "SQLMap Agent")


app = workflow.compile()
result = app.invoke({
    "docker_image": "ON",
    "website": ""
})
print(result)

