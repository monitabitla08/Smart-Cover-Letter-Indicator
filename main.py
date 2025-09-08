import os
import pathlib
import yaml
from dotenv import load_dotenv

from crewai import Agent, Task, Crew, Process, LLM

# ---------- the paths ----------
ROOT = pathlib.Path(__file__).parent
INPUTS = ROOT / "inputs"
OUTPUTS = ROOT / "outputs"
AGENTS_YAML = ROOT / "agents.yaml"
TASKS_YAML = ROOT / "tasks.yaml"

# ---------- the helpers ----------
def read_file(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8").strip()

def ensure_outputs():
    OUTPUTS.mkdir(parents=True, exist_ok=True)

def load_yaml(p: pathlib.Path) -> dict:
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def resolve_llm(llm_id: str | None) -> LLM:
    # Fallback to env MODEL if llm_id is None
    model_name = llm_id or os.getenv("MODEL", "openai/gpt-4o-mini")
    # You can pass temperature, max_tokens, base_url, etc., if needed:
    return LLM(model=model_name, temperature=0.2)

# ---------- boot ----------
def main():
    load_dotenv()
    ensure_outputs()

    # Load inputs
    resume_path = INPUTS / "resume.txt"
    jd_path = INPUTS / "job_description.txt"
    if not resume_path.exists() or not jd_path.exists():
        raise FileNotFoundError(
            f"Missing input files. Expected:\n- {resume_path}\n- {jd_path}"
        )
    resume_text = read_file(resume_path)
    jd_text = read_file(jd_path)

    # Loading configs
    agents_cfg = load_yaml(AGENTS_YAML)
    tasks_cfg = load_yaml(TASKS_YAML)

    # Building agents from the YAML
    matcher_cfg = agents_cfg["resume_matcher"]
    cover_cfg = agents_cfg["cover_letter_writer"]

    matcher = Agent(
        role=matcher_cfg["role"],
        goal=matcher_cfg["goal"],
        backstory=matcher_cfg["backstory"],
        llm=resolve_llm(matcher_cfg.get("llm")),
        verbose=True,
    )

    # resume_enhancer = Agent(
    #     role=cover_cfg["role"],
    #     goal=cover_cfg["goal"],
    #     backstory=cover_cfg["backstory"],
    #     llm=resolve_llm(cover_cfg.get("llm")),
    #     verbose=False,
    # )
    cover_writer = Agent(
        role=cover_cfg["role"],
        goal=cover_cfg["goal"],
        backstory=cover_cfg["backstory"],
        llm=resolve_llm(cover_cfg.get("llm")),
        verbose=True,
    )

    # Building tasks from YAML + inject content
    match_t_cfg = tasks_cfg["match_task"]
    cover_t_cfg = tasks_cfg["cover_letter_task"]

    match_description = (
        match_t_cfg["description"]
        + "\n\n---\n# RESUME\n"
        + resume_text
        + "\n\n---\n# JOB DESCRIPTION\n"
        + jd_text
    )

    match_task = Task(
        description=match_description,
        expected_output=match_t_cfg["expected_output"],
        agent=matcher,
        output_file=match_t_cfg.get("output_file", str(OUTPUTS / "match_report_1.md")),
    )

    cover_description = (
        cover_t_cfg["description"]
        + "\n\n(You have access to the prior Gap/Match Report via task context.)"
        + "\n\n---\n# RESUME\n"
        + resume_text
        + "\n\n---\n# JOB DESCRIPTION\n"
        + jd_text
    )

    cover_task = Task(
        description=cover_description,
        expected_output=cover_t_cfg["expected_output"],
        agent=cover_writer,
        context=[match_task],
        output_file=cover_t_cfg.get("output_file", str(OUTPUTS / "cover_letter.md")),
    )

    crew = Crew(
        agents=[matcher, cover_writer],
        tasks=[match_task, cover_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    # Combine the final deliverable in the required order
    combined = []
    match_out = read_file(OUTPUTS / "match_report.md")
    cover_out = read_file(OUTPUTS / "cover_letter.md")
    combined.append("# Gap/Match Report\n\n" + match_out)
    combined.append("\n\n---\n\n# Cover Letter\n\n" + cover_out)

    (OUTPUTS / "report_and_cover_letter.md").write_text(
        "\n".join(combined), encoding="utf-8"
    )

    print("\nDone! See:")
    print(f"  - {OUTPUTS / 'match_report.md'}")
    print(f"  - {OUTPUTS / 'cover_letter.md'}")
    print(f"  - {OUTPUTS / 'report_and_cover_letter.md'}  (combined)")

if __name__ == "__main__":
    main()