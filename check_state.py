import json


def main():
    """Print status of all task results from the aider agents state file."""
    state = json.load(open('.aider-agents-state.json', encoding='utf-8'))
    for r in state['task_results']:
        status = 'OK' if r['success'] else 'FAIL'
        print(f"[{status}] {r['subtask_id']}: {r['output'][-300:]}")


if __name__ == '__main__':
    main()
