#!/usr/bin/env python
# -*- coding: utf-8 -*-

from shutil import rmtree
from subprocess import Popen, PIPE
from tempfile import mkdtemp

from reflex.error import GitCommandError


class PrestineRepo():
    """
    Creates a context with a temporary clone of a given repository.

    This repo that may be manipulated safely without worrying about performing
    actions on a real local copy of the repo. The repo has the 'origin' remote
    configured for the clone uri which is passed in during initialization. It
    also provides some useful helper methods that can be preformed on the repo
    itself.
    """

    def __init__(self, clone_uri, prod_branch=None, dev_branch=None):
        if not prod_branch:
            prod_branch = 'master'
        if not dev_branch:
            dev_branch = 'develop'

        self.dir = mkdtemp()
        self.clone_uri = clone_uri
        self.production_branch = prod_branch
        self.development_branch = dev_branch

    def __enter__(self):
        self.git('clone', self.clone_uri, self.dir)
        self.git('fetch', 'origin')
        return self

    def __exit__(self, *exc):
        rmtree(self.dir)

    def git(self, *args):
        """ Git command helper.
        """
        command = ['git'] + list(args)
        result = Popen(command, cwd=self.dir, stdout=PIPE, stderr=PIPE)
        result.wait()
        if result.returncode != 0:
            err = result.stderr.readlines()
            print('\n'.join(err))
            raise GitCommandError(
                "Failed to run '{}'.".format(' '.join(command)),
                err
            )
        return result

    def branches(self, match=None):
        """ List all branches matching an optional pattern in a repo.
        """
        args = ['--list', '--remote']
        if match:
            args.append(match)
        result = self.git('branch', *args)
        branches = [branch.strip() for branch in result.stdout.readlines()]
        return branches

    def branch_exists(self, full_branch_name):
        """ Returns True or False depending on if a branch exists or not.
        """
        return full_branch_name in self.branches()

    def checkout(self, branch_name, reset_sha=None):
        """ Checks out a git reference in a repo with the option to hard reset.
        """
        if self.branch_exists('origin/{}'.format(branch_name)):
            self.git('checkout', branch_name)
        else:
            self.git('checkout', '-b', branch_name)
        if reset_sha:
            self.git('reset', '--hard', reset_sha)

    def tag(self, tag, message, sha=None):
        """ Creates an annotated tag on the repo at the provided sha (Or HEAD).
        """
        args = []
        if sha:
            args.append(sha)
        return self.git('tag', '--annotate', '--message', message, tag, *args)

    def get_last_tag(self, sha=None, match=None):
        """
        Returns the latest tag on a given tree. Can also filter by tags
        matching the match argument.
        """
        options = ['--abbrev=0']
        if match:
            options += ['--match', match]
        if sha:
            options.append(sha)
        return self.git('describe', *options).stdout.read().strip()
