from typing import Dict, Any, List
import re

class InputGuardrail:
    """
    Guardrail for checking input safety.
    Handles length checks, prompt injection, and topic relevance.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        # Load thresholds from config if they exist, otherwise use defaults
        safety_cfg = config.get("safety", {})
        self.min_length = safety_cfg.get("min_query_length", 5)
        self.max_length = safety_cfg.get("max_query_length", 2000)
        # Prohibited categories for the report documentation
        self.policy_categories = ["harmful_content", "prompt_injection", "off_topic"]

    def validate(self, query: str) -> Dict[str, Any]:
        violations = []

        # 1. Length Checks
        if len(query) < self.min_length:
            violations.append({"validator": "length", "reason": "Query too short", "severity": "low"})
        if len(query) > self.max_length:
            violations.append({"validator": "length", "reason": "Query too long", "severity": "medium"})

        # 2. Prompt Injection Checks
        violations.extend(self._check_prompt_injection(query))

        # 3. Toxicity Checks (Keyword Heuristic)
        violations.extend(self._check_toxic_language(query))

        # 4. Relevance Checks
        violations.extend(self._check_relevance(query))

        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "sanitized_input": query 
        }

    def _check_toxic_language(self, text: str) -> List[Dict[str, Any]]:
        violations = []
        # Basic prohibited word list (expand this for your report)
        prohibited = ["hate", "violence", "illegal", "exploit"]
        for word in prohibited:
            if word in text.lower():
                violations.append({
                    "validator": "harmful_content",
                    "reason": f"Prohibited content detected: {word}",
                    "severity": "high"
                })
        return violations

    def _check_prompt_injection(self, text: str) -> List[Dict[str, Any]]:
        violations = []
        injection_patterns = [
            r"ignore (all )?previous instructions",
            r"system (prompt|message)",
            r"forget everything",
            r"reveal your (secret|internal) prompt"
        ]
        for pattern in injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append({
                    "validator": "prompt_injection",
                    "reason": "Potential instruction override attempt detected",
                    "severity": "high"
                })
        return violations

    def _check_relevance(self, query: str) -> List[Dict[str, Any]]:
        violations = []
        # Check if the query is at least vaguely related to HCI or Research
        hci_keywords = ["hci", "interaction", "user", "design", "research", "technology", "study"]
        if not any(word in query.lower() for word in hci_keywords):
            violations.append({
                "validator": "off_topic",
                "reason": "Query appears unrelated to HCI research topics",
                "severity": "medium"
            })
        return violations