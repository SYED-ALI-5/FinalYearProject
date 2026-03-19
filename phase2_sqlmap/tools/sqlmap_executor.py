import asyncio
import re
import time
import subprocess
from typing import Optional, Dict, Any, Tuple
from datetime import datetime


class SQLMapExecutor:
    def __init__(
        self, 
        use_host: bool = True,
        output_dir: str = "/tmp/sqlmap"
    ):
        self.use_host = use_host
        self.output_dir = output_dir

    async def run_command(self, command: list[str]) -> Tuple[str, str, int]:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return (
            stdout.decode('utf-8', errors='ignore'),
            stderr.decode('utf-8', errors='ignore'),
            process.returncode or 0
        )

    async def is_sqlmap_installed(self) -> bool:
        try:
            result = subprocess.run(["which", "sqlmap"], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    async def install_sqlmap(self):
        print("[SQLMapExecutor] Installing SQLMap...")
        result = subprocess.run(["brew", "install", "sqlmap"], capture_output=True, text=True)
        if result.returncode != 0:
            print("[SQLMapExecutor] Could not install via brew. Trying pip...")
            result = subprocess.run(["pip", "install", "sqlmap"], capture_output=True, text=True)

    async def ensure_sqlmap(self):
        if not await self.is_sqlmap_installed():
            await self.install_sqlmap()

    def _get_dvwa_cookie(self) -> str:
        try:
            with open("/tmp/dvwa_session.txt", "r") as f:
                return f.read().strip()
        except:
            return "PHPSESSID=test; security=low"
    
    def _parse_url(self, cmd_parts: list) -> tuple:
        for i, part in enumerate(cmd_parts):
            if part == "-u":
                url = cmd_parts[i+1].strip("'\"")
                base_url = url.split("?")[0] if "?" in url else url
                cmd_parts[i+1] = f"'{base_url}'"
                return cmd_parts, base_url
        return cmd_parts, None
    
    async def execute_sqlmap(
        self, 
        command: str,
        timeout: int = 300
    ) -> Dict[str, Any]:
        await self.ensure_sqlmap()
        
        print(f"[SQLMapExecutor] Original: {command}")
        
        start_time = time.time()
        
        cmd_parts = command.split()
        
        if "dvwa" in command.lower() or ":8081" in command:
            cookie = self._get_dvwa_cookie()
            cmd_parts, _ = self._parse_url(cmd_parts)
            cmd_parts.append("--data=id=1&Submit=Submit")
            cmd_parts.append(f"--cookie={cookie}")
            print(f"[SQLMapExecutor] Modified: {' '.join(cmd_parts)}")
        
        try:
            stdout, stderr, return_code = await self.run_command(cmd_parts)
        except Exception as e:
            return {
                'command_executed': command,
                'stdout': '',
                'stderr': str(e),
                'return_code': -1,
                'vulnerability_found': False,
                'execution_time': 0,
                'error': str(e)
            }
        
        execution_time = time.time() - start_time
        
        vulnerability_found = self._check_vulnerability_found(stdout)
        db_type = self._extract_database_type(stdout)
        vulnerable_param = self._extract_vulnerable_parameter(stdout)
        
        return {
            'command_executed': command,
            'stdout': stdout,
            'stderr': stderr,
            'return_code': return_code,
            'vulnerability_found': vulnerability_found,
            'vulnerable_parameter': vulnerable_param,
            'database_type': db_type,
            'execution_time': execution_time,
            'timestamp': datetime.now().isoformat()
        }

    def _check_vulnerability_found(self, output: str) -> bool:
        vulnerability_indicators = [
            "is vulnerable",
            "vulnerability(ies) found",
            "Parameter:",
            "Type:",
            "Title:",
            "Payload:",
            "the back-end DBMS is",
            "you have successfully logged into",
            "sqlmap identified the following injection",
            "appears to be '",
            "appears to be injectable"
        ]
        
        false_positive_indicators = [
            "false positive",
            "does not seem to be injectable",
            "not injectable"
        ]
        
        output_lower = output.lower()
        
        for fp in false_positive_indicators:
            if fp in output_lower:
                return False
            
        for indicator in vulnerability_indicators:
            if indicator.lower() in output_lower:
                return True
        
        return False

    def _extract_database_type(self, output: str) -> Optional[str]:
        patterns = [
            r"back-end DBMS: (\w+)",
            r"Database: (\w+)",
            r"DBMS: (\w+)",
            r"the back-end DBMS is '(\w+)'"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

    def _extract_vulnerable_parameter(self, output: str) -> Optional[str]:
        patterns = [
            r"Parameter: (\w+)",
            r"Vulnerable parameter: (\w+)",
            r"--parameter=(\w+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

    def generate_dvwa_command(
        self,
        target_url: str,
        parameter: str = "id",
        risk: int = 2,
        level: int = 1
    ) -> str:
        command = f"sqlmap -u '{target_url}?{parameter}=1'"
        command += f" -p {parameter}"
        command += f" --risk={risk} --level={level}"
        command += " --batch"
        command += " --random-agent"
        command += " --dbms=mysql"
        
        return command

    def generate_juice_shop_command(
        self,
        target_url: str,
        parameter: str = "q",
        risk: int = 1,
        level: int = 1
    ) -> str:
        command = f"sqlmap -u '{target_url}?{parameter}=test'"
        command += f" -p {parameter}"
        command += f" --risk={risk} --level={level}"
        command += " --batch"
        command += " --random-agent"
        
        return command
