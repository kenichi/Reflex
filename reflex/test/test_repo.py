#!/usr/bin/env python
# -*- coding: utf-8 -*-

from subprocess import PIPE

import pytest
from mock import call, Mock, patch

from reflex.repo import PrestineRepo
from reflex.error import GitCommandError


def test_prestinerepo_creation():
    """
    Ensure that a brand new git repo is created when using PrestineRepo.
    """
    temp_dir = '/tmp/aorta_tmp'
    clone_uri = 'no'
    mResult = Mock()
    mResult.returncode = 0
    mockTmpdir = patch('reflex.repo.mkdtemp', return_value=temp_dir)
    mockPopen = patch('reflex.repo.Popen', return_value=mResult)
    mockRmtree = patch('reflex.repo.rmtree')

    with mockTmpdir as pTmpdir, mockPopen as pPopen, mockRmtree as pRmtree:
        with PrestineRepo(clone_uri) as repo:
            pTmpdir.assert_called_with()
            pPopen.assert_has_calls([
                call(['git', 'clone', clone_uri, temp_dir],
                     cwd=temp_dir, stderr=PIPE, stdout=PIPE),
                call(['git', 'fetch', 'origin'],
                     cwd=temp_dir, stderr=PIPE, stdout=PIPE),
            ])
            assert repo.dir == temp_dir
            assert repo.clone_uri == clone_uri
            assert repo.production_branch == 'master'
            assert repo.development_branches == ['develop']
        pRmtree.assert_called_with(temp_dir)


@patch('reflex.repo.mkdtemp', return_value='/tmp')
def test_git(_):
    """
    Ensure that git is properly called when using `PrestineRepo#git`.
    """
    repo = PrestineRepo('/tmp/stop')
    mResult = Mock()
    mResult.returncode = 0
    mockPopen = patch('reflex.repo.Popen', return_value=mResult)
    with mockPopen as patchPopen:
        repo.git('command')
        patchPopen.assert_called_with(
            ['git', 'command'], cwd='/tmp', stderr=PIPE, stdout=PIPE)


@patch('reflex.repo.mkdtemp', return_value='/tmp')
def test_failed_git_command(_):
    """
    Ensure a GitCommandError is raised if a git command fails in a
    PrestineRepo.
    """
    repo = PrestineRepo('/tmp/stop')
    mResult = Mock()
    mResult.returncode = 1
    mockPopen = patch('reflex.repo.Popen', return_value=mResult)
    with mockPopen:
        with pytest.raises(GitCommandError):
            repo.git('command')


@patch('reflex.repo.mkdtemp', return_value='/tmp')
def test_branches(_):
    """
    Ensure git branches are listed when calling PrestineRepo#branches.
    """
    branches_readlines = [
        '  brightmd/master\n',
        '  brightmd/stable\n',
        '  brightmd/develop\n',
    ]

    repo = PrestineRepo('/tmp/stop')
    mResult = Mock()
    mResult.returncode = 0
    mResult.stdout.readlines.return_value = branches_readlines
    mockPopen = patch('reflex.repo.Popen', return_value=mResult)
    with mockPopen as patchPopen:
        assert repo.branches() == ['brightmd/master', 'brightmd/stable',
                                   'brightmd/develop']
        repo.branches('shrubbery')
        patchPopen.assert_has_calls([
            call(['git', 'branch', '--list', '--remote'], cwd='/tmp',
                 stderr=PIPE, stdout=PIPE),
            call(['git', 'branch', '--list', '--remote', 'shrubbery'],
                 cwd='/tmp', stderr=PIPE, stdout=PIPE),
        ])


@patch('reflex.repo.mkdtemp', return_value='/tmp')
def test_branch_exists(_):
    """
    Ensure PrestineRepo#branch_exists returns True when the given branch exists
    in a repo and False when the given branch does not exist in a repo.
    """
    repo = PrestineRepo('/tmp/stop')
    mRepo = patch.object(repo, 'branches', side_effect=['brancha', 'branchb'])
    with mRepo:
        assert repo.branch_exists('brancha')
        assert not repo.branch_exists('branchc')


@patch('reflex.repo.mkdtemp', return_value='/tmp')
def test_checkout_new(_):
    """
    Ensure PrestineRepo#checkout creates a new branch when it does not exist on
    a repo.
    """
    repo = PrestineRepo('/tmp/stop')
    mRepo = patch.object(repo, 'branch_exists', side_effect=[False, False])
    mResult = Mock()
    mResult.returncode = 0
    mockPopen = patch('reflex.repo.Popen', return_value=mResult)
    with mRepo, mockPopen as patchPopen:
        repo.checkout('branch')
        repo.checkout('branch', 'abcdef12345')

        patchPopen.assert_has_calls([
            call(['git', 'checkout', '-b', 'branch'], cwd='/tmp', stderr=PIPE,
                 stdout=PIPE),
            call(['git', 'checkout', '-b', 'branch'], cwd='/tmp', stderr=PIPE,
                 stdout=PIPE),
            call(['git', 'reset', '--hard', 'abcdef12345'], cwd='/tmp',
                 stderr=PIPE, stdout=PIPE),
        ])


@patch('reflex.repo.mkdtemp', return_value='/tmp')
def test_checkout_existing(_):
    """
    Ensure PrestineRepo#checkout checks out an existing branch if it does exist
    on the repo.
    """
    repo = PrestineRepo('/tmp/stop')
    mRepo = patch.object(repo, 'branch_exists', side_effect=[True, True])
    mResult = Mock()
    mResult.returncode = 0
    mockPopen = patch('reflex.repo.Popen', return_value=mResult)
    with mRepo, mockPopen as patchPopen:
        repo.checkout('branch')
        repo.checkout('branch', 'abcdef12345')

        patchPopen.assert_has_calls([
            call(['git', 'checkout', 'branch'], cwd='/tmp', stderr=PIPE,
                 stdout=PIPE),
            call(['git', 'checkout', 'branch'], cwd='/tmp', stderr=PIPE,
                 stdout=PIPE),
            call(['git', 'reset', '--hard', 'abcdef12345'], cwd='/tmp',
                 stderr=PIPE, stdout=PIPE),
        ])


@patch('reflex.repo.mkdtemp', return_value='/tmp')
def test_tag(_):
    """
    Ensure PrestineRepo#tag creates annotated tags at a given sha on the repo.
    """
    repo = PrestineRepo('/tmp/stop')
    mResult = Mock()
    mResult.returncode = 0
    mockPopen = patch('reflex.repo.Popen', return_value=mResult)
    with mockPopen as patchPopen:
        repo.tag('test-1.0.0', 'test tag')
        repo.tag('release-1.0.0', 'release tag', 'abcdef12345')

        patchPopen.assert_has_calls([
            call(['git', 'tag', '--annotate', '--message', 'test tag',
                  'test-1.0.0'], cwd='/tmp', stderr=PIPE, stdout=PIPE),
            call(['git', 'tag', '--annotate', '--message', 'release tag',
                  'release-1.0.0', 'abcdef12345'], cwd='/tmp', stderr=PIPE,
                 stdout=PIPE),
        ])


@patch('reflex.repo.mkdtemp', return_value='/tmp')
def test_get_last_tag(_):
    """
    Ensure PrestineRepo#get_last_tag calls `git describe --abbrev=0` to get the
    last tag on a repo.
    """
    tag = b'  1.3.5\n'

    repo = PrestineRepo('/tmp/stop')
    mResult = Mock()
    mResult.returncode = 0
    mResult.stdout.read.return_value = tag
    mockPopen = patch('reflex.repo.Popen', return_value=mResult)
    with mockPopen as patchPopen:
        repo.get_last_tag()
        repo.get_last_tag('abc')
        repo.get_last_tag('abc', 'test-*')
        repo.get_last_tag(match='test-*')

        patchPopen.assert_has_calls([
            call(['git', 'describe', '--abbrev=0'], cwd='/tmp', stderr=PIPE,
                 stdout=PIPE),
            call(['git', 'describe', '--abbrev=0', 'abc'], cwd='/tmp',
                 stderr=PIPE, stdout=PIPE),
            call(['git', 'describe', '--abbrev=0', '--match', 'test-*', 'abc'],
                 cwd='/tmp', stderr=PIPE, stdout=PIPE),
            call(['git', 'describe', '--abbrev=0', '--match', 'test-*'],
                 cwd='/tmp', stderr=PIPE, stdout=PIPE),
        ])

        assert repo.get_last_tag() == '1.3.5'


@patch('reflex.repo.mkdtemp', return_value='/tmp')
def test_get_last_release(_):
    """
    Ensure PrestineRepo#get_last_release calls PrestineRepo#get_last_tag with
    'release-*' to filter out any non-release tags on the repo.
    """
    repo = PrestineRepo('/tmp/stop')
    mRepo = patch.object(repo, 'get_last_tag', side_effect=['release-1.0.0'])
    with mRepo:
        assert repo.get_last_release('sha') == 'release-1.0.0'
        repo.get_last_tag.assert_called_with('sha', 'release-*')
