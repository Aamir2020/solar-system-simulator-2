"""Build release notes from commits since the nearest earlier reachable tag."""
import argparse
import string
import subprocess
from pathlib import Path


def git(directory, *arguments, check=True):
    return subprocess.run(['git', '--no-pager', *arguments], cwd=directory,
                          capture_output=True, text=True, encoding='utf-8',
                          errors='replace', check=check)


def markdown(value):
    return ''.join('\\' + character if character in string.punctuation else character
                   for character in value)


def generate_notes(directory, repository, tag):
    current = git(directory, 'rev-parse', '--verify', f'refs/tags/{tag}^{{commit}}').stdout.strip()
    previous = git(directory, 'describe', '--tags', '--abbrev=0', f'--exclude={tag}',
                   current, check=False)
    if previous.returncode not in (0, 128):
        previous.check_returncode()
    previous_tag = previous.stdout.strip() if previous.returncode == 0 else ''
    if previous_tag:
        base = git(directory, 'rev-parse', '--verify',
                   f'refs/tags/{previous_tag}^{{commit}}').stdout.strip()
        revision_range = f'{base}..{current}'
        introduction = f'Changes since **{markdown(previous_tag)}**.'
    else:
        revision_range = current
        introduction = 'Initial release: commits included in this version.'
    history = git(directory, '-c', 'i18n.logOutputEncoding=utf-8', 'log', '--reverse',
                  '--no-decorate', '--no-show-signature',
                  '--format=%H%x00%s%x00', revision_range).stdout.split('\0')
    lines = ['## Commit changelog', '', introduction, '']
    for index in range(0, len(history)-1, 2):
        commit, subject = history[index].strip(), history[index+1].strip()
        lines.append(f'- {markdown(subject)} ([{commit[:7]}]'
                     f'(https://github.com/{repository}/commit/{commit}))')
    if len(lines) == 4:
        lines.append('No new commits since the previous tag.')
    return previous_tag, '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True, help='Existing release tag')
    parser.add_argument('--repository', required=True, help='GitHub owner/repository')
    parser.add_argument('--directory', type=Path, default=Path.cwd(), help='Local Git checkout')
    parser.add_argument('--output', type=Path, required=True, help='Release notes Markdown file')
    args = parser.parse_args()
    try:
        previous, notes = generate_notes(args.directory, args.repository, args.tag)
        args.output.write_text(notes, encoding='utf-8')
    except (OSError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))
    print(previous)  # The workflow uses the same starting tag for GitHub's PR notes.


if __name__ == '__main__':
    main()
