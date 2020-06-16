#!/usr/bin/env python
# -*- coding: utf-8 -*-

from subprocess import Popen

import pytest
from click.testing import CliRunner
from mock import Mock, patch, ANY

import reflex.cli as cli
from reflex.error import (
    DuplicateGitReference, InvalidGitReference, InvalidUpgradePath,
)
from reflex.repo import PrestineRepo


@pytest.fixture
def releaseable_repo(tmpdir):
    """
    Fixture which sets up a mock upstream to push final changes to in tests
    without the need for a git server or live repo somewhere.
    """
    tempdir = str(tmpdir.mkdir('reflex-releaseable'))

    result = Popen(['git', 'init', '--bare', '.'], cwd=tempdir)
    result.wait()
    with PrestineRepo(tempdir) as repo:
        # SVC-873 use a default other than 'master' by implicitly creating 'main'
        repo.git('checkout', '-b', 'main')

        # Setup a test repo which has commits that are ready to be released.
        repo.git('config', 'user.email', 'ci@test.com')
        repo.git('config', 'user.name', 'ci')
        repo.git('commit', '--allow-empty', '-m', 'initial commit')
        repo.git('tag', '-a', 'release-1.0.0', '-m', 'release-1.0.0')
        repo.git('checkout', '-b', 'develop')
        for i in range(3):
            repo.git('commit', '--allow-empty', '-m', 'commit {}'.format(i))
        repo.git('push', 'origin', 'main:main')
        repo.git('push', 'origin', 'develop:develop')

        # Ensure we are always on the main branch in this repo before handing
        # off to the underlying test.
        repo.git('checkout', 'main')
        yield repo


def test_validate_upgrade():
    """
    Ensure upgrades upgrade from only valid upgrade paths.
    """
    can_upgrade = [
        ('1.0.0', '1.0.1'),
        ('1.0.0', '1.1.0'),
        ('1.0.0', '2.0.0'),
        ('1.0.0', '3.2.1'),
        ('0.0.0', '1.2.3'),
        ('1.2.5', '1.9.1'),
        ('1.11.1', '1.12.3'),
        ('1.11.1', '2.0.0'),
    ]
    fails_upgrade = [
        ('1.0.0', '1.0.0'),
        ('1.0.1', '1.0.0'),
        ('1.1.0', '1.0.0'),
        ('2.0.0', '1.0.0'),
        ('3.2.1', '1.0.0'),
        ('1.2.3', '0.0.0'),
        ('1.9.5', '1.8.9'),
        ('1.19.3', '1.13.1'),
        ('2.0.0', '1.13.1'),
    ]

    for path in can_upgrade:
        assert cli.validate_upgrade(*path)

    for path in fails_upgrade:
        with pytest.raises(InvalidUpgradePath):
            cli.validate_upgrade(*path)


def test_create_new_release(releaseable_repo, capsys):
    """
    Ensure release branch is created when creating a new release.
    """
    cli.create_release(releaseable_repo, 'develop', '1.0.1')
    out, err = capsys.readouterr()

    assert not err
    assert '1.0.1' in out
    assert 'origin/test-1.0.1' in releaseable_repo.branches()


def test_not_recreate_release(releaseable_repo):
    """
    Ensure reflex does not create multiple release branches with the same
    version.
    """
    with pytest.raises(InvalidUpgradePath):
        cli.create_release(releaseable_repo, 'develop', '1.0.0')

    assert 'origin/test-1.0.0' not in releaseable_repo.branches()


def test_not_create_earlier_release(releaseable_repo):
    """
    Ensure reflex does not open a release branch using a version before the
    latest released version.
    """
    with pytest.raises(InvalidUpgradePath):
        cli.create_release(releaseable_repo, 'develop', '0.9.0')

    assert 'origin/test-0.9.0' not in releaseable_repo.branches()


def test_existing_branches_warning(releaseable_repo, capsys):
    """
    Ensure reflex warns users about unclosed release branches.
    """
    releaseable_repo.git('checkout', '-b', 'test-1.1.0')
    releaseable_repo.git('push', 'origin', 'test-1.1.0')

    assert 'origin/test-1.1.0' in releaseable_repo.branches()

    cli.create_release(releaseable_repo, 'develop', '1.2.0')
    out, err = capsys.readouterr()

    assert '1.2.0' in out
    assert 'origin/test-1.1.0' in err


def test_will_not_open_existing_test_branch(releaseable_repo):
    """
    Ensure reflex does not open an already opened release branch.
    """
    releaseable_repo.git('checkout', '-b', 'test-1.1.0')
    releaseable_repo.git('push', 'origin', 'test-1.1.0')
    assert 'origin/test-1.1.0' in releaseable_repo.branches()

    with pytest.raises(DuplicateGitReference):
        cli.create_release(releaseable_repo, 'develop', '1.1.0')


def test_hotfix(releaseable_repo):
    """
    Ensure hotfix release branches are forked from the production branch.
    """
    mockCreateRelease = patch('reflex.cli.create_release', Mock())
    with mockCreateRelease as pCreateRelease:
        cli.hotfix(releaseable_repo)
        pCreateRelease.assert_called_with(
            releaseable_repo, 'release-1.0.0', None)


def test_release(releaseable_repo):
    """
    Ensure release branches are forked from the development branch.
    """
    mockCreateRelease = patch('reflex.cli.create_release')
    with mockCreateRelease as pCreateRelease:
        cli.release(releaseable_repo)
        pCreateRelease.assert_called_with(
            releaseable_repo, 'develop', None)


def test_cannot_complete_re_release(releaseable_repo):
    """
    Ensure a release branch cannot be closed if an invalid upgrade path is
    detected.
    """
    with pytest.raises(InvalidUpgradePath):
        cli.complete_release(releaseable_repo, '1.0.0')


def test_cannot_complete_non_existant_release(releaseable_repo):
    """
    Ensure a release cannot be closed if a release branch for the version
    releasing does not exist.
    """
    with pytest.raises(InvalidGitReference):
        cli.complete_release(releaseable_repo, '1.1.0')


def test_merges_into_multiple_dev_branches(releaseable_repo):
    """
    Ensure if multiple development branches are specified during closing a
    release that changes are merged down to each development branch.
    """
    dev_release = releaseable_repo.get_last_tag('develop', 'release-*')
    assert dev_release == 'release-1.0.0'

    releaseable_repo.git('checkout', '-b', 'develop-2')
    releaseable_repo.git('commit', '--allow-empty', '-m', 'Testing commit')
    releaseable_repo.git('push', 'origin', 'develop-2')
    releaseable_repo.git('checkout', 'main')
    cli.create_release(releaseable_repo, 'develop', '1.1.0')

    releaseable_repo.development_branches = ['develop', 'develop-2']
    cli.complete_release(releaseable_repo, '1.1.0')

    dev_release = releaseable_repo.get_last_tag('develop', 'release-*')
    dev_2_release = releaseable_repo.get_last_tag('develop-2', 'release-*')

    assert dev_release == 'release-1.1.0'
    assert dev_2_release == 'release-1.1.0'


def test_deletes_release_branch_after_release(releaseable_repo):
    """
    Ensure that a release branch is automatically cleaned up after closing a
    release.
    """
    cli.create_release(releaseable_repo, 'develop', '1.1.0')
    assert 'origin/test-1.1.0' in releaseable_repo.branches()
    cli.complete_release(releaseable_repo, '1.1.0')
    assert 'origin/test-1.1.0' not in releaseable_repo.branches()


def test_tag_is_created_for_release(releaseable_repo, capsys):
    """
    Ensure that a final release tag is created when closing a release.
    """
    cli.create_release(releaseable_repo, 'develop', '1.1.0')
    assert releaseable_repo.get_last_release('main') == 'release-1.0.0'
    cli.complete_release(releaseable_repo, '1.1.0')
    assert releaseable_repo.get_last_release('main') == 'release-1.1.0'

    out, err = capsys.readouterr()
    assert "Successfully closed" in out
    assert "release-1.1.0" in out
    assert not err


def test_create_release_main(releaseable_repo):
    """
    Ensure release creation is called when passing in the '--release' flag.
    """
    mockRelease = patch('reflex.cli.release', Mock())
    with mockRelease as pRelease:
        runner = CliRunner()
        runner.invoke(cli.main, [
            '1.1.0',
            '--repo', releaseable_repo.dir,
            '--release'
        ])
        assert pRelease.called_once_with(ANY, 'develop', '1.1.0')


def test_create_hotfix_main(releaseable_repo):
    """
    Ensure hotfix creation is called when passing in the '--hotfix' flag.
    """
    mockHotfix = patch('reflex.cli.hotfix', Mock())
    with mockHotfix as pHotfix:
        runner = CliRunner()
        runner.invoke(cli.main, [
            '1.1.0',
            '--repo', releaseable_repo.dir,
            '--hotfix'
        ])
        assert pHotfix.called_once_with(ANY, '1.0.0', '1.1.0')


def test_close_release_main(releaseable_repo):
    """
    Ensure a release is closed when passing in the '--close' flag.
    """
    mockClose = patch('reflex.cli.complete_release', Mock())
    with mockClose as pClose:
        runner = CliRunner()
        runner.invoke(cli.main, [
            '1.1.0',
            '--repo', releaseable_repo.dir,
            '--close'
        ])
        assert pClose.called_once_with(ANY, '1.1.0')


def test_reflex_without_action(releaseable_repo):
    """
    Ensure reflex fails when not given an action to take on a repo.
    """
    runner = CliRunner()
    result = runner.invoke(cli.main, ['1.1.0', '--repo', releaseable_repo.dir])

    assert 'Invalid' in result.output
    assert result.exit_code == 1


def test_reflex_with_multiple_action(releaseable_repo):
    """
    Ensure reflex fails when given multiple options to take on a repo.
    """
    runner = CliRunner()
    result = runner.invoke(cli.main, [
        '1.1.0',
        '--repo', releaseable_repo.dir,
        '--release',
        '--close',
    ])

    assert 'Invalid' in result.output
    assert result.exit_code == 1
