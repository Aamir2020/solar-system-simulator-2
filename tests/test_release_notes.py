"""Exercise real Git history without publishing releases or contacting GitHub."""
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.release_notes import generate_notes


class ReleaseNotesTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Release tests')
        self.git('config', 'user.email', 'release-tests@example.invalid')
        self.initial = self.commit('Initial application')

    def git(self, *arguments):
        return subprocess.check_output(
            ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
             '-c', 'tag.gpgSign=false', *arguments], cwd=self.directory,
            text=True, encoding='utf-8', stderr=subprocess.STDOUT).strip()

    def commit(self, subject):
        self.git('commit', '--allow-empty', '-m', subject)
        return self.git('rev-parse', 'HEAD')

    def test_first_release_includes_every_commit_with_links(self):
        fix = self.commit('Fix planet selection')
        self.git('tag', 'v1.0.0')
        previous, notes = generate_notes(self.directory, 'owner/simulator', 'v1.0.0')
        self.assertEqual(previous, '')
        self.assertIn('Initial release', notes)
        self.assertIn('Initial application', notes)
        self.assertIn(f'https://github.com/owner/simulator/commit/{fix}', notes)
        self.assertLess(notes.index('Initial application'), notes.index('Fix planet selection'))

    def test_subsequent_release_excludes_previous_release_and_later_commits(self):
        self.git('tag', '-a', 'v1.0.0', '-m', 'First release')
        feature = self.commit('Add textured planets')
        self.git('tag', 'v1.1.0')
        self.commit('Unreleased work')
        previous, notes = generate_notes(self.directory, 'owner/simulator', 'v1.1.0')
        self.assertEqual(previous, 'v1.0.0')
        self.assertIn(feature, notes)
        self.assertNotIn('Initial application', notes)
        self.assertNotIn('Unreleased work', notes)

    def test_tags_on_unrelated_branches_do_not_change_the_range(self):
        self.git('tag', 'v1.0.0')
        self.git('switch', '-c', 'other')
        self.commit('Unrelated experiment')
        self.git('tag', 'v9.0.0')
        self.git('switch', 'main')
        self.commit('Fix Saturn rings')
        self.git('tag', 'v1.0.1')
        previous, notes = generate_notes(self.directory, 'owner/simulator', 'v1.0.1')
        self.assertEqual(previous, 'v1.0.0')
        self.assertNotIn('Unrelated experiment', notes)
        self.assertIn('Fix Saturn rings', notes)

    def test_merged_feature_commits_are_included(self):
        self.git('tag', 'v1.0.0')
        self.git('switch', '-c', 'feature')
        self.commit('Add 3D camera')
        self.git('switch', 'main')
        self.commit('Update README')
        self.git('merge', '--no-ff', 'feature', '-m', 'Merge 3D feature')
        self.git('tag', 'v1.1.0')
        _, notes = generate_notes(self.directory, 'owner/simulator', 'v1.1.0')
        self.assertIn('Add 3D camera', notes)
        self.assertIn('Update README', notes)

    def test_same_commit_tags_report_no_new_changes(self):
        self.git('tag', 'v1.0.0')
        self.git('tag', 'v1.0.1')
        previous, notes = generate_notes(self.directory, 'owner/simulator', 'v1.0.1')
        self.assertEqual(previous, 'v1.0.0')
        self.assertIn('No new commits', notes)

    def test_commit_subjects_are_literal_markdown_and_preserve_unicode(self):
        self.git('tag', 'v1.0.0')
        self.commit('Fix [Saturn] and `rings` — café')
        self.git('tag', 'v1.0.1')
        _, notes = generate_notes(self.directory, 'owner/simulator', 'v1.0.1')
        self.assertIn('Fix \\[Saturn\\] and \\`rings\\` — café', notes)

    def test_missing_release_tag_fails(self):
        with self.assertRaises(subprocess.CalledProcessError):
            generate_notes(self.directory, 'owner/simulator', 'missing')
