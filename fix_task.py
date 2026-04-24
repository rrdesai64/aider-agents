"""Script to fix the file argument handling in agents/task.py."""


def fix_task_file():
    """Fix the Aider command construction to properly pass files with --file flags."""
    path = 'agents/task.py'
    content = open(path, encoding='utf-8').read()
    content = content.replace(
        'all_files = files_to_edit + files_to_create\n        if all_files:\n            cmd += all_files',
        'all_files = files_to_edit + files_to_create\n        for f in all_files:\n            cmd += ["--file", f]'
    )
    open(path, 'w', encoding='utf-8').write(content)
    print('Fixed.')


if __name__ == '__main__':
    fix_task_file()
