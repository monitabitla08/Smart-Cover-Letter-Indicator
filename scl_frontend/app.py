from flask import Flask, render_template, request, jsonify
import os
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).parent.parent))
from main import Crew, Agent, Task, Process, resolve_llm, load_yaml

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run', methods=['POST'])
def run_crew():
    data = request.json
    resume_text = data.get('resume', '').strip()
    jd_text = data.get('job_description', '').strip()
    if not resume_text or not jd_text:
        return jsonify({'error': 'Both resume and job description are required.'}), 400

    # Load configs
    ROOT = pathlib.Path(__file__).parent.parent
    AGENTS_YAML = ROOT / 'agents.yaml'
    TASKS_YAML = ROOT / 'tasks.yaml'
    agents_cfg = load_yaml(AGENTS_YAML)
    tasks_cfg = load_yaml(TASKS_YAML)

    matcher_cfg = agents_cfg['resume_matcher']
    cover_cfg = agents_cfg['cover_letter_writer']

    matcher = Agent(
        role=matcher_cfg['role'],
        goal=matcher_cfg['goal'],
        backstory=matcher_cfg['backstory'],
        llm=resolve_llm(matcher_cfg.get('llm')),
        verbose=False,
    )
    cover_writer = Agent(
        role=cover_cfg['role'],
        goal=cover_cfg['goal'],
        backstory=cover_cfg['backstory'],
        llm=resolve_llm(cover_cfg.get('llm')),
        verbose=False,
    )

    match_t_cfg = tasks_cfg['match_task']
    cover_t_cfg = tasks_cfg['cover_letter_task']

    match_description = (
        match_t_cfg['description']
        + '\n\n---\n# RESUME\n'
        + resume_text
        + '\n\n---\n# JOB DESCRIPTION\n'
        + jd_text
    )
    match_task = Task(
        description=match_description,
        expected_output=match_t_cfg['expected_output'],
        agent=matcher,
    )
    cover_description = (
        cover_t_cfg['description']
        + '\n\n(You have access to the prior Gap/Match Report via task context.)'
        + '\n\n---\n# RESUME\n'
        + resume_text
        + '\n\n---\n# JOB DESCRIPTION\n'
        + jd_text
    )
    cover_task = Task(
        description=cover_description,
        expected_output=cover_t_cfg['expected_output'],
        agent=cover_writer,
        context=[match_task],
    )
    crew = Crew(
        agents=[matcher, cover_writer],
        tasks=[match_task, cover_task],
        process=Process.sequential,
        verbose=False,
    )
    crew.kickoff()
    # Read outputs from tasks
    # match_output = match_task.output or ''
    # cover_output = cover_task.output or ''
    # return jsonify({'gaps': match_output, 'cover_letter': cover_output})

    match_output = str(match_task.output or '')
    cover_output = str(cover_task.output or '')
    return jsonify({'gaps': match_output, 'cover_letter': cover_output})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
