import asyncio

class DockerAgent:
    def __init__(self, working_dir="../FinalYearProject/docker",
                 kali_container="kali"):
        
        self.working_dir = working_dir
        self.kali_container = kali_container

    # --------------------------------
    # Generic shell execution on host
    # --------------------------------
    async def run_host_command(self, command: list[str]) -> str:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=self.working_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(stderr.decode())

        return stdout.decode()

    # --------------------------------
    # Execute command inside Kali container
    # --------------------------------
    async def run_in_kali(self, command: list[str]) -> str:
        full_command = ["docker", "exec", self.kali_container] + command
        return await self.run_host_command(full_command)

    # --------------------------------
    # Check if Kali container is running
    # --------------------------------
    async def is_kali_running(self) -> bool:
        try:
            output = await self.run_host_command(
                ["docker", "inspect", "-f", "{{.State.Running}}", self.kali_container]
            )
            return "true" in output.lower()
        except:
            return False

    # --------------------------------
    # Start docker compose
    # --------------------------------
    async def start_lab(self):
        print("[DockerAgent] Starting docker compose lab...")
        await self.run_host_command(["docker", "compose", "up", "-d"])

    # --------------------------------
    # Check if tool exists inside Kali
    # --------------------------------
    async def is_tool_installed(self, tool: str) -> bool:
        try:
            await self.run_in_kali(["which", tool])
            return True
        except:
            return False

    # --------------------------------
    # Install tool dynamically
    # --------------------------------
    async def install_tool(self, tool: str):
        print(f"[DockerAgent] Installing {tool} inside Kali...")

        await self.run_in_kali(["apt", "update"])
        await self.run_in_kali(["apt", "install", "-y", tool])
