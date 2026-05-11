"""
AutoGen-Based Orchestrator (Updated for AutoGen 0.4.x)
This orchestrator coordinates the research workflow using a RoundRobinGroupChat.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from src.agents.autogen_agents import create_research_team

class AutoGenOrchestrator:
    """
    Orchestrates multi-agent research using AutoGen's RoundRobinGroupChat.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("autogen_orchestrator")
        self.logger.info("Creating research team...")
        self.team = create_research_team(config)
        self.workflow_trace: List[Dict[str, Any]] = []

    def process_query(self, query: str, max_rounds: int = 20) -> Dict[str, Any]:
        self.logger.info(f"Processing query: {query}")
        try:
            # Handle async loop management for various environments
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(
                        asyncio.run, 
                        self._process_query_async(query, max_rounds)
                    ).result()
            else:
                result = loop.run_until_complete(self._process_query_async(query, max_rounds))
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing query: {e}", exc_info=True)
            return {
                "query": query,
                "error": str(e),
                "response": f"An error occurred: {str(e)}",
                "conversation_history": [],
                "metadata": {"error": True}
            }
    
    async def _process_query_async(self, query: str, max_rounds: int = 20) -> Dict[str, Any]:
        task_message = f"""Research Query: {query}

Please work together to answer this query:
1. Planner: Create a research plan.
2. Researcher: Gather evidence from web and academic sources.
3. Writer: Synthesize findings into a well-cited response.
4. Critic: Evaluate the quality and provide feedback."""
        
        # Run the team
        result = await self.team.run(task=task_message)
        
        # UPDATED: In newer AutoGen versions, result.messages is a standard list
        messages = []
        for message in result.messages:
            msg_dict = {
                "source": message.source if hasattr(message, 'source') else "System",
                "content": str(message.content) if hasattr(message, 'content') else str(message),
            }
            messages.append(msg_dict)
        
        # Extract the final synthesized response (usually from Writer)
        final_response = ""
        for msg in reversed(messages):
            if msg.get("source") in ["Writer", "Critic"]:
                final_response = msg.get("content", "")
                break
        
        if not final_response and messages:
            final_response = messages[-1].get("content", "")
        
        return self._extract_results(query, messages, final_response)

    def _extract_results(self, query: str, messages: List[Dict[str, Any]], final_response: str = "") -> Dict[str, Any]:
        research_findings = []
        plan = ""
        critique = ""
        
        for msg in messages:
            source = msg.get("source", "")
            content = msg.get("content", "")
            if source == "Planner" and not plan:
                plan = content
            elif source == "Researcher":
                research_findings.append(content)
            elif source == "Critic":
                critique = content
        
        # Clean up termination keyword
        if final_response:
            final_response = final_response.replace("TERMINATE", "").strip()
        
        return {
            "query": query,
            "response": final_response,
            "conversation_history": messages,
            "metadata": {
                "num_messages": len(messages),
                "num_sources": len(research_findings),
                "plan": plan,
                "critique": critique,
                "agents_involved": list(set([msg.get("source", "") for msg in messages])),
            }
        }