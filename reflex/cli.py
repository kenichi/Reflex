#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

import click

from reflex.repo import PrestineRepo
from reflex.error import (InvalidUpgradePath, DuplicateGitReference)


@click.command()
@click.argument('version')
@click.option('--release', help='Create a release branch', is_flag=True)
@click.option('--hotfix', help='Create a hotfix branch', is_flag=True)
@click.option('--close', help='Close and tag a release/hotfix branch',
              is_flag=True)
@click.option('--repo', 'git_uri', required=True,
              envvar="REPO", help='Path to a git repo to perform actions on.')
def main(version, git_uri, **kwargs):
    """ Tool for the automating the release process in a repository.
    """
    action = None
    for flag, enabled in kwargs.iteritems():
        if enabled:
            action = flag
            break

    action = {
        'release': release,
        'hotfix': hotfix,
        'close': complete_release,
    }.get(action)

    if action:
        with PrestineRepo(git_uri) as repo:
            action(repo, version)
    else:
        print("Invalid subcommand.")


def validate_upgrade(_from, to):
    """ Returns True if two versions can be upgraded with regard to semver.
    """
    ver_from_parts = _from.split('-')[-1].split('.')
    ver_to_parts = to.split('-')[-1].split('.')
    ver_parts = zip(ver_from_parts, ver_to_parts)

    for ver_part in ver_parts:
        if int(ver_part[-1]) > int(ver_part[0]):
            return True
    else:
        raise InvalidUpgradePath("Unable to upgrade from '{}' to '{}'.".format(
            _from, to))


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
    if version.startswith('release-'):
        version = version.split('-')[-1]
    testing_branch = 'test-{}'.format(version)
    release_tag = 'release-{}'.format(version)

    print("Closing {}.".format(testing_branch))

    latest_release = repo.get_last_tag('master', 'release-*')
    validate_upgrade(latest_release, release_tag)

    # First we merge the release branch into branches locally.
    repo.checkout('master', 'origin/master')
    repo.git('merge', '--no-ff', 'origin/{}'.format(testing_branch))
    repo.tag(release_tag, 'Release tag for {}'.format(version))

    # Merge master to develop to absorb any release bugfixes.
    repo.checkout('develop', 'origin/develop')
    repo.git('merge', '--no-ff', 'master')

    # Push all local changes in the end if all else works properly.
    repo.git('push', 'origin', 'master')
    repo.git('push', 'origin', release_tag)
    repo.git('push', 'origin', 'develop')

    # Finally delete the release branch
    repo.git('push', 'origin', ':{}'.format(testing_branch))

    print("Successfully closed release branch '{}' as '{}' on master.".format(
        testing_branch, release_tag))


def hotfix(repo, version=None):
    """ Create a hotfix release branch.
    """
    sha = repo.get_last_tag('origin/master', 'release-*')
    print("Creating new hotfix branch off of {}.".format(sha))
    repo.checkout('master', sha)
    create_release(repo, sha, version)


def release(repo, version=None):
    """ Create a normal release branch.
    """
    sha = 'develop'
    print("Creating new release branch off of {}.".format(sha))
    repo.checkout(sha, 'origin/{}'.format(sha))
    create_release(repo, sha, version)


def create_release(repo, sha, version):
    """ Create a release branch for running tests.
    """
    last_version = repo.get_last_tag('{}'.format(sha), 'release-*')
    validate_upgrade(last_version, version)

    if version.startswith('release-'):
        version = version.split('-')[-1]

    test_branches = [x for x in repo.branches('origin/test-*') if re.match(
        r'origin/test-\d+(\.\d+){2}', x)]

    if test_branches:
        print("!! Warning, the following sprint testing branches are open:")
        for branch in test_branches:
            print("!!\t* {}".format(branch))

    testing_branch = 'test-{}'.format(version)
    if repo.branch_exists('origin/{}'.format(testing_branch)):
        raise DuplicateGitReference(
            "Oops! Looks like {} already exists!".format(testing_branch))

    repo.checkout(testing_branch, sha)

    repo.git('push', 'origin', testing_branch)

    print("Successfully opened release branch '{}' for testing.".format(
        testing_branch
    ))
