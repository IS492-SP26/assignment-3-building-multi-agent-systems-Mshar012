from typing import Dict, Any, List
import re

class OutputGuardrail:
    """
    Guardrail for checking output safety.
    Handles PII redaction, harmful content detection, and hallucination checks.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        safety_cfg = config.get("safety", {})
        self.enable_redaction = safety_cfg.get("enable_redaction", True)

    def validate(self, response: str, sources: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        violations = []

        # 1. Check for PII (Personal Identifiable Information)
        pii_violations = self._check_pii(response)
        violations.extend(pii_violations)

        # 2. Check for Harmful Content
        harmful_violations = self._check_harmful_content(response)
        violations.extend(harmful_violations)

        # 3. Fact-Checking (Simple Source Verification)
        if sources:
            consistency_violations = self._check_factual_consistency(response, sources)
            violations.extend(consistency_violations)

        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "sanitized_output": self._sanitize(response, violations) if violations else response
        }

    def _check_pii(self, text: str) -> List[Dict[str, Any]]:
        violations = []
        patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
        }

        for pii_type, pattern in patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                violations.append({
                    "validator": "pii",
                    "pii_type": pii_type,
                    "reason": f"Detected {pii_type} in response",
                    "severity": "high",
                    "matches": matches
                })
        return violations

    def _check_harmful_content(self, text: str) -> List[Dict[str, Any]]:
        violations = []
        # Detection for biased or harmful summaries
        toxic_terms = ["stereotype", "offensive", "unethical"]
        for term in toxic_terms:
            if term in text.lower():
                violations.append({
                    "validator": "harmful_content",
                    "reason": f"Response contains potentially toxic terminology: {term}",
                    "severity": "medium"
                })
        return violations

    def _check_factual_consistency(self, response: str, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        violations = []
        # Basic check: Ensure the response mentions at least one URL from the sources
        source_urls = [s.get("url", "") for s in sources if s.get("url")]
        if source_urls and not any(url in response for url in source_urls):
            violations.append({
                "validator": "hallucination",
                "reason": "Response does not include verifiable source links from research",
                "severity": "medium"
            })
        return violations

    def _sanitize(self, text: str, violations: List[Dict[str, Any]]) -> str:
        sanitized = text
        for violation in violations:
            # Redact PII automatically
            if violation.get("validator") == "pii":
                for match in violation.get("matches", []):
                    sanitized = sanitized.replace(match, "[REDACTED]")
            
            # For high-severity harmful content, return a refusal
            if violation.get("severity") == "high" and violation.get("validator") == "harmful_content":
                return "The system generated a response that violates safety policies and has been blocked."
        
        return sanitized