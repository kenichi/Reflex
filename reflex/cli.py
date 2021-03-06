#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys

import click

from reflex.repo import PrestineRepo
from reflex.error import (
    DuplicateGitReference, InvalidGitReference, InvalidUpgradePath,
)


@click.command()
@click.argument('version')
@click.option('--release', help='Create a release branch', is_flag=True)
@click.option('--hotfix', help='Create a hotfix branch', is_flag=True)
@click.option('--close', help='Close and tag a release/hotfix branch',
              is_flag=True)
@click.option('--repo', 'git_uri', required=True,
              envvar="REPO", help='Path to a git repo to perform actions on.')
@click.option('--production-branch', 'prod_branch', default='main',
              help='The production branch where release tags should live.')
@click.option('--development-branch', 'develop_branch', default=['develop'],
              help='The development branch where new work should live.',
              multiple=True)
def main(version, git_uri, prod_branch, develop_branch, **kwargs):
    """ Tool for the automating the release process in a repository.
    """
    action = []
    for flag, enabled in kwargs.items():
        if enabled:
            action.append(flag)
    if len(action) != 1:
        sys.stderr.write("Invalid subcommand.\nSpecify a single action.\n")
        sys.exit(1)

    action = {
        'release': release,
        'hotfix': hotfix,
        'close': complete_release,
    }.get(action[0])

    with PrestineRepo(git_uri, prod_branch, develop_branch) as repo:
        action(repo, version)


def validate_upgrade(_from, to):
    """ Returns True if two versions can be upgraded with regard to semver.
    """
    ver_from_parts = _from.split('-')[-1].split('.')
    ver_to_parts = to.split('-')[-1].split('.')
    ver_parts = zip(ver_from_parts, ver_to_parts)

    for ver_part in ver_parts:
        if int(ver_part[0]) < int(ver_part[-1]):
            return True
        elif int(ver_part[0]) > int(ver_part[-1]):
            break
    raise InvalidUpgradePath(
        "Unable to upgrade from '{}' to '{}'.".format(_from, to))


def complete_release(repo, version=None, **kwargs):
    """ Closes a release branch.

    This function performs a few tasks useful for closing a release branch.
      - It first makes sure that the release branch can be closed with the
        given version by running through the validate_upgrade test.
      - The function then creates a merge commit on the 'production' branch of
        the repo and generates a release tag on the merge commit.
      - Then merges the 'production' branch down to the 'development' branch.
      - Once all of the above complete successfully we push the local copy of
        the repo up to the main repo.
      - After the release branch has been merged successfully into 'production'
        and 'development' we can delete the release branch from upstream.
    """
    testing_branch = 'test-{}'.format(version)
    release_tag = 'release-{}'.format(version)

    sys.stdout.write("Closing {}.\n".format(testing_branch))

    repo.checkout(repo.production_branch)
    latest_release = repo.get_last_release(repo.production_branch)
    validate_upgrade(latest_release, release_tag)

    test_branches = [x for x in repo.branches('origin/test-*') if re.match(
        r'origin/test-\d+(\.\d+){2}', x)]

    if "origin/{}".format(testing_branch) not in test_branches:
        raise InvalidGitReference("Unable to find {} to close release".format(
            testing_branch))

    # First we merge the release branch into branches locally.
    repo.checkout(repo.production_branch, 'origin/{}'.format(
        repo.production_branch))
    repo.git('merge', '--no-ff', 'origin/{}'.format(testing_branch))
    repo.tag(release_tag, 'Release tag for {}'.format(version))

    # Merge production to development to absorb any release bugfixes.
    for branch in repo.development_branches:
        repo.checkout(branch, 'origin/{}'.format(branch))
        repo.git('merge', '--no-ff', repo.production_branch)

    # Push all local changes in the end if all else works properly.
    repo.git('push', 'origin', repo.production_branch)
    repo.git('push', 'origin', release_tag)
    for branch in repo.development_branches:
        repo.git('push', 'origin', branch)

    # Finally delete the release branch
    repo.git('push', 'origin', ':{}'.format(testing_branch))

    sys.stdout.write("Successfully closed release branch '{}' as '{}' on "
                     "{}.\n".format(
                         testing_branch, release_tag, repo.production_branch))


def hotfix(repo, version=None):
    """ Create a hotfix release branch.
    """
    sha = repo.get_last_release('origin/{}'.format(repo.production_branch))
    sys.stdout.write("Creating new hotfix branch off of {}.\n".format(sha))
    repo.checkout(repo.production_branch, sha)
    create_release(repo, sha, version)


def release(repo, version=None):
    """ Create a normal release branch.
    """
    sha, = repo.development_branches
    sys.stdout.write("Creating new release branch off of {}.\n".format(sha))
    repo.checkout(sha, 'origin/{}'.format(sha))
    create_release(repo, sha, version)


def create_release(repo, sha, version):
    """ Create a release branch for running tests.
    """
    last_version = repo.get_last_release(sha)
    validate_upgrade(last_version, version)

    test_branches = [x for x in repo.branches('origin/test-*') if re.match(
        r'origin/test-\d+(\.\d+){2}', x)]

    if test_branches:
        sys.stderr.write("!! Warning, the following sprint testing branches "
                         "are open:\n")
        for branch in test_branches:
            sys.stderr.write("!!\t* {}\n".format(branch))

    testing_branch = 'test-{}'.format(version)
    if repo.branch_exists('origin/{}'.format(testing_branch)):
        raise DuplicateGitReference(
            "Oops! Looks like {} already exists!\n".format(testing_branch))

    repo.checkout(testing_branch, sha)

    repo.git('push', 'origin', testing_branch)

    sys.stdout.write("Successfully opened release branch '{}' for "
                     "testing.\n".format(testing_branch))
