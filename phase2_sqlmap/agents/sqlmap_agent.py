from typing import List, Optional, Dict, Any, Union
from langchain_ollama import ChatOllama
from models.sqlmap_models import SQLMapCommand, HTTPMethod
from services.neo4j_retriever import Neo4jRetriever
import json
import re


class SQLMapAgent:
    def __init__(
        self, 
        llm: ChatOllama, 
        neo4j: Optional[Neo4jRetriever] = None,
        default_risk: int = 2,
        default_level: int = 2
    ):
        self.llm = llm
        self.neo4j = neo4j
        self.default_risk = default_risk
        self.default_level = default_level

    def generate_sqlmap_command(self, target: Union[Dict[str, Any], str]) -> str:
        if isinstance(target, str):
            url = target
            parameter = "id"
        else:
            url = target.get('url', '')
            parameter = target.get('parameter', 'id')
        
        url_with_param = f"{url}?{parameter}=1"
        cmd = f"sqlmap -u '{url_with_param}'"
        cmd += f" -p {parameter}"
        cmd += f" --risk={self.default_risk}"
        cmd += f" --level={self.default_level}"
        cmd += " --batch"
        cmd += " --random-agent"
        cmd += " --dbms=mysql"
        
        if "dvwa" in url.lower():
            cmd += " --cookie='PHPSESSID=test; security=low'"
        
        return cmd

    def _validate_and_fix_command(self, cmd: str) -> str:
        if not cmd.startswith('sqlmap'):
            cmd = 'sqlmap ' + cmd
        
        cmd = re.sub(r'\s+-r\b', ' ', cmd)
        cmd = re.sub(r'\s+--parameter=(\S+)', r' -p \1', cmd)
        cmd = re.sub(r'\s+--risk=(\S+)', r' --risk=\1', cmd)
        cmd = re.sub(r'\s+--level=(\S+)', r' --level=\1', cmd)
        
        if '-u' not in cmd and '--url' not in cmd:
            cmd = cmd.replace('sqlmap', 'sqlmap -u', 1)
        
        return cmd

    def _clean_json_response(self, content: str) -> str:
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        content = content.replace('\n', ' ').replace('\r', '')
        content = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', content)
        
        content = content.strip()
        
        return content

    async def generate_command_with_llm(
        self, 
        target: Union[Dict[str, Any], str],
        context: Optional[str] = None
    ) -> SQLMapCommand:
        if isinstance(target, str):
            url = target
            parameter = "id"
        else:
            url = target.get('url', '')
            parameter = target.get('parameter', 'id')
        
        full_url = f"{url}?{parameter}=1"
        prompt = f"Return ONLY this exact text, nothing else: sqlmap -u '{full_url}' -p {parameter} --risk=2 --level=2 --batch --dbms=mysql"
        
        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content.strip() if hasattr(response, 'content') else str(response)
            
            if not content.startswith('sqlmap'):
                content = f"sqlmap -u '{full_url}' -p {parameter} --risk=2 --level=2 --batch --dbms=mysql"
            
            return SQLMapCommand(
                url=url,
                parameter=parameter,
                method=HTTPMethod.GET,
                command=content,
                risk=self.default_risk,
                level=self.default_level
            )
        except Exception as e:
            print(f"LLM error: {e}. Using default command.")
            return SQLMapCommand(
                url=url,
                parameter=parameter,
                method=HTTPMethod.GET,
                command=self.generate_sqlmap_command(target),
                risk=self.default_risk,
                level=self.default_level
            )

    async def generate_commands_for_targets(
        self, 
        targets: List[Union[Dict[str, Any], str]],
        use_llm: bool = False
    ) -> List[SQLMapCommand]:
        commands = []
        
        for target in targets:
            if use_llm:
                try:
                    cmd = await self.generate_command_with_llm(target)
                    commands.append(cmd)
                except Exception as e:
                    print(f"Error: {e}")
                    commands.append(SQLMapCommand(
                        url=str(target) if isinstance(target, str) else target.get('url', ''),
                        parameter="id",
                        method=HTTPMethod.GET,
                        command=self.generate_sqlmap_command(target),
                        risk=self.default_risk,
                        level=self.default_level
                    ))
            else:
                commands.append(SQLMapCommand(
                    url=str(target) if isinstance(target, str) else target.get('url', ''),
                    parameter="id",
                    method=HTTPMethod.GET,
                    command=self.generate_sqlmap_command(target),
                    risk=self.default_risk,
                    level=self.default_level
                ))
        
        return commands
