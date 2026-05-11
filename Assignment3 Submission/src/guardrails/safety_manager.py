from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import json
from src.guardrails.input_guardrail import InputGuardrail
from src.guardrails.output_guardrail import OutputGuardrail

class SafetyManager:
    """
    Coordinates safety guardrails and logs safety events.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.log_events = config.get("log_events", True)
        self.logger = logging.getLogger("safety")
        
        # Initialize the two guardrail modules
        self.input_guardrail = InputGuardrail(config)
        self.output_guardrail = OutputGuardrail(config)

        self.safety_events: List[Dict[str, Any]] = []
        self.prohibited_categories = ["harmful_content", "prompt_injection", "off_topic", "pii", "hallucination"]

    def check_input_safety(self, query: str) -> Dict[str, Any]:
        if not self.enabled:
            return {"safe": True, "violations": [], "sanitized_input": query}

        result = self.input_guardrail.validate(query)
        is_safe = result["valid"]

        if not is_safe and self.log_events:
            self._log_safety_event("input", query, result["violations"], is_safe)

        return {
            "safe": is_safe,
            "violations": result["violations"],
            "sanitized_input": result["sanitized_input"]
        }

    def check_output_safety(self, response: str, sources: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        if not self.enabled:
            return {"safe": True, "violations": [], "response": response}

        result = self.output_guardrail.validate(response, sources)
        is_safe = result["valid"]

        if not is_safe and self.log_events:
            self._log_safety_event("output", response, result["violations"], is_safe)

        return {
            "safe": is_safe,
            "violations": result["violations"],
            "response": result["sanitized_output"]
        }

    def _log_safety_event(self, event_type: str, content: str, violations: List[Dict[str, Any]], is_safe: bool):
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "safe": is_safe,
            "violations": violations,
            "content_preview": content[:100] + "..." if len(content) > 100 else content
        }
        self.safety_events.append(event)
        self.logger.warning(f"Safety Violation: {event_type} - {len(violations)} issues found.")

    def get_safety_events(self) -> List[Dict[str, Any]]:
        return self.safety_events