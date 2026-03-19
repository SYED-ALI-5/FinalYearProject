from neo4j import AsyncGraphDatabase
from typing import List, Optional, Dict, Any
import json


class Neo4jRetriever:
    def __init__(self, uri: str = "bolt://127.0.0.1:7687", 
                 user: str = "neo4j", password: str = "testpassword"):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None

    async def connect(self):
        self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))

    async def close(self):
        if self.driver:
            await self.driver.close()

    async def run_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not self.driver:
            await self.connect()
        
        async with self.driver.session() as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    async def get_all_hosts(self) -> List[Dict[str, Any]]:
        query = """
        MATCH (h:Host)
        RETURN h.ip as ip, h.status as status
        ORDER BY h.ip
        """
        return await self.run_query(query)

    async def get_hosts_with_ports(self) -> List[Dict[str, Any]]:
        query = """
        MATCH (h:Host)-[:HAS_PORT]->(p:Port)
        RETURN h.ip as ip, h.status as status, p.number as port, p.protocol as protocol
        ORDER BY h.ip, p.number
        """
        return await self.run_query(query)

    async def get_web_targets(self) -> List[Dict[str, Any]]:
        query = """
        MATCH (h:Host)-[:HAS_PORT]->(p:Port)-[:RUNS]->(s:Service)
        WHERE s.name IN ['http', 'https']
        RETURN h.ip as ip, 
               p.number as port, 
               s.name as service
        ORDER BY p.number
        """
        results = await self.run_query(query)
        
        web_targets = []
        for r in results:
            protocol = "https" if r.get('service') == 'https' else "http"
            port = r.get('port', 80 if protocol == 'http' else 443)
            url = f"{protocol}://{r.get('ip')}"
            if (protocol == "http" and port != 80) or (protocol == "https" and port != 443):
                url += f":{port}"
            
            web_targets.append({
                'url': url,
                'ip': r.get('ip'),
                'port': port,
                'service': r.get('service')
            })
        
        return web_targets

    async def get_endpoints_with_parameters(self) -> List[Dict[str, Any]]:
        query = """
        MATCH (e:Endpoint)
        RETURN e.url as url, 
               e.method as method, 
               e.parameter as parameter
        ORDER BY e.url
        """
        return await self.run_query(query)

    async def get_full_recon_data(self) -> Dict[str, Any]:
        hosts = await self.get_all_hosts()
        web_targets = await self.get_web_targets()
        endpoints = await self.get_endpoints_with_parameters()
        
        return {
            'hosts': hosts,
            'web_targets': web_targets,
            'endpoints': endpoints,
            'total_hosts': len(hosts),
            'total_web_targets': len(web_targets),
            'total_endpoints': len(endpoints)
        }

    async def store_sqlmap_workflow(
        self,
        endpoint_url: str,
        sqlmap_command: str,
        result_summary: str,
        vulnerability_found: bool
    ) -> bool:
        query = """
        MERGE (ra:ReconAgent {name: 'ReconAgent'})
        MERGE (e:Endpoint {url: $url})
        MERGE (sa:SQLMapAgent {name: 'SQLMapAgent'})
        MERGE (gq:GeneratedQuery {command: $command})
        MERGE (da:DockerAgent {name: 'DockerAgent'})
        MERGE (er:ExecutionResult {summary: $summary, vulnerable: $vulnerable})
        
        MERGE (ra)-[:DISCOVERED]->(e)
        MERGE (sa)-[:GENERATED]->(gq)
        MERGE (gq)-[:TARGETS]->(e)
        MERGE (da)-[:EXECUTED]->(gq)
        MERGE (gq)-[:PRODUCED]->(er)
        
        RETURN er
        """
        try:
            await self.run_query(query, {
                'url': endpoint_url,
                'command': sqlmap_command,
                'summary': result_summary,
                'vulnerable': vulnerability_found
            })
            return True
        except Exception as e:
            print(f"Error storing workflow: {e}")
            return False

    async def store_generated_query(self, endpoint_url: str, sqlmap_command: str) -> bool:
        query = """
        MERGE (sa:SQLMapAgent {name: 'SQLMapAgent'})
        MERGE (e:Endpoint {url: $url})
        MERGE (gq:GeneratedQuery {
            command: $command,
            timestamp: datetime()
        })
        
        MERGE (sa)-[:GENERATED]->(gq)
        MERGE (gq)-[:TARGETS]->(e)
        
        RETURN gq
        """
        try:
            await self.run_query(query, {
                'url': endpoint_url,
                'command': sqlmap_command
            })
            return True
        except Exception as e:
            print(f"Error storing generated query: {e}")
            return False

    async def store_execution_result(
        self,
        sqlmap_command: str,
        result_summary: str,
        vulnerable: bool,
        db_type: Optional[str] = None
    ) -> bool:
        query = """
        MATCH (gq:GeneratedQuery {command: $command})
        MERGE (er:ExecutionResult {
            summary: $summary,
            vulnerable: $vulnerable,
            database_type: $db_type,
            timestamp: datetime()
        })
        
        MERGE (gq)-[:PRODUCED]->(er)
        
        RETURN er
        """
        try:
            await self.run_query(query, {
                'command': sqlmap_command,
                'summary': result_summary,
                'vulnerable': vulnerable,
                'db_type': db_type
            })
            return True
        except Exception as e:
            print(f"Error storing execution result: {e}")
            return False

    async def get_workflow_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        query = """
        MATCH path = (ra:ReconAgent)-[:DISCOVERED]->(e:Endpoint)
                     <-[:TARGETS]-(gq:GeneratedQuery)
                     <-[:EXECUTED]-(da:DockerAgent)
                     <-[:PRODUCED]-(er:ExecutionResult)
        RETURN e.url as endpoint,
               gq.command as sqlmap_command,
               er.summary as result,
               er.vulnerable as vulnerable,
               er.timestamp as timestamp
        ORDER BY er.timestamp DESC
        LIMIT $limit
        """
        return await self.run_query(query, {'limit': limit})
