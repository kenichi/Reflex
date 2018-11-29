#!/usr/bin/env python
# -*- coding: utf-8 -*-


class GitCommandError(Exception):
    """ Exception which can be raised when git exits with a non-zero exit code.
    """
    pass


class InvalidUpgradePath(Exception):
    """
    Exception which is thrown if an invalid upgrade path is detected. This
    is usually when attempting to upgrade to a version before the one that is
    already the latest version.
    """
    pass


class DuplicateGitReference(Exception):
    """
    Exception which is thrown when unable to create a tag/branch/ect. as it
    already exists in the repo.
    """
    pass
