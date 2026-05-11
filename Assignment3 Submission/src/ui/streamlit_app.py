import sys
from pathlib import Path
import streamlit as st
import asyncio
import yaml
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.autogen_orchestrator import AutoGenOrchestrator

load_dotenv()

def load_config():
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {}

def initialize_session_state():
    if 'history' not in st.session_state:
        st.session_state.history = []
    if 'orchestrator' not in st.session_state:
        config = load_config()
        try:
            st.session_state.orchestrator = AutoGenOrchestrator(config)
        except Exception as e:
            st.error(f"Failed to initialize orchestrator: {e}")
            st.session_state.orchestrator = None
    if 'show_traces' not in st.session_state:
        st.session_state.show_traces = True
    if 'show_safety_log' not in st.session_state:
        st.session_state.show_safety_log = True

async def process_query(query: str) -> Dict[str, Any]:
    orchestrator = st.session_state.orchestrator
    if orchestrator is None:
        return {"query": query, "response": "System not initialized.", "citations": [], "metadata": {}}
    
    result = orchestrator.process_query(query)
    
    # Process conversation for UI display
    messages = result.get("conversation_history", [])
    agent_traces = {}
    for msg in messages:
        src = msg.get("source", "Unknown")
        if src not in agent_traces: agent_traces[src] = []
        agent_traces[src].append(msg.get("content", ""))

    return {
        "query": query,
        "response": result.get("response", ""),
        "citations": [m.get("content") for m in messages if "http" in m.get("content", "")],
        "metadata": {
            "agent_traces": agent_traces,
            "num_sources": result.get("metadata", {}).get("num_sources", 0),
            "safety_violations": result.get("violations", [])
        }
    }

def display_response(result: Dict[str, Any]):
    # Safety Check Display
    violations = result.get("metadata", {}).get("safety_violations", [])
    if violations:
        st.error("🛡️ Safety Policy Triggered")
        for v in violations:
            st.warning(f"**{v['validator'].upper()}**: {v['reason']}")

    st.markdown("### 📝 Synthesized Research Report")
    st.info(result.get("response", "No response generated."))

    # Traces
    if st.session_state.show_traces:
        st.markdown("### 🔍 Agent Workflow Traces")
        traces = result.get("metadata", {}).get("agent_traces", {})
        for agent, logs in traces.items():
            with st.expander(f"Agent: {agent}", expanded=False):
                for log in logs:
                    st.caption(log)

def main():
    st.set_page_config(page_title="HCI Research AI", page_icon="🤖", layout="wide")
    initialize_session_state()
    st.title("🤖 HCI Multi-Agent Researcher")
    
    query = st.text_input("Enter your research question:", placeholder="e.g. Current trends in VR accessibility")
    
    if st.button("Generate Report", type="primary"):
        if query:
            with st.spinner("Agents are collaborating..."):
                res = asyncio.run(process_query(query))
                display_response(res)

if __name__ == "__main__":
    main()