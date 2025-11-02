import os, json, textwrap, time
from datetime import datetime
from core.ai_bridge.openai_bridge import chat_json

# --- CORE CONFIGURATION & SETUP ---
TARGET_MODEL = os.getenv("RESEARCH_MODEL", "gpt-5-turbo")  # adjust to your best available model
OUT_DIR = "outputs/research"
os.makedirs(OUT_DIR, exist_ok=True)

RESEARCH_SYSTEM = """
You are a senior AI research strategist. Your job is to design the best possible plan to build a production-grade bot/agent.
Deliver brutally practical recommendations, focused on profit, speed, and reliability. Cite specific tools/APIs and give copy-ready prompts.
Output strict JSON with keys exactly as requested.
"""

RESEARCH_USER_TMPL = """
AGENT_NAME: {agent_name}
OBJECTIVE: {objective}
CONSTRAINTS: {constraints}

REQUIRED_OUTPUT (JSON with these keys):
- "executive_summary": short paragraph of what to build and why it will work
- "best_tools": list of {{"name","why","links"}}
- "model_strategy": list of {{"task","model","settings"}}
- "prompt_kits": list of {{"name","purpose","prompt_template"}}
- "data_inputs": list of {{"source","fields"}}
- "automation": list of {{"cron","trigger","action"}}
- "success_metrics": list of KPIs
- "risks_and_mitigations": list of {{"risk","mitigation"}}
- "build_spec": {{
    "files": [{{"path","purpose"}}],
    "env_vars": ["NAME=description", ...],
    "cli_examples": ["...", "..."]
}}
"""

class ResearchBot:
    def run(self, agent_name: str, objective: str, constraints: str = "Budget sensitive; minimal human ops.") -> dict:
        user = RESEARCH_USER_TMPL.format(agent_name=agent_name, objective=objective, constraints=constraints)
        raw = chat_json(TARGET_MODEL, RESEARCH_SYSTEM, user, max_tokens=2800)
        try:
            data = json.loads(raw)
        except Exception:
            # try to salvage
            data = json.loads(raw.strip().split("{",1)[-1].rsplit("}",1)[0].join(["{","}"]))
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        outpath = os.path.join(OUT_DIR, f"research_{agent_name.lower().replace(' ','_')}_{ts}.json")
        with open(outpath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[OK] Research report → {outpath}")
        return data
