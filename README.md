Reflex
======

"The reflex is then an automatic response to a stimulus that does not receive
or need conscious thought."

Reflex is our tool to handle various git repository administration so that us
humans don't have to.

Installation
============

```sh
python setup.py develop
```

Usage
=====

Reflex adds the `reflex` command to your command line which can be used to help
make the release process easier, such as automatically creating and closing
release/hotfix branches. There are also some helpers involved which make sure
that releases happen in order and are not duplicated, ect.

To create a brand new release branch simply run
```sh
reflex 1.0.1 --release --repo git@github.com:brightmd/reflex.git
```
This will create a branch with all of the changes in develop onto a branch
named `test-1.0.1`. This is the release branch which developers can begin
testing and bugfixes on.

After a release branch is deemed 'releasable' and all of the bugs that have
been found have been fixed in it you can close the release branch with reflex
again.
```sh
reflex 1.0.1 --close --repo git@github.com:brightmd/reflex.git
```
This command automatically merges the `test-1.0.1` branch into `main` and
then into `develop` to make sure that all changes are picked up everywhere.
It also creates a `release-1.0.1` tag on the `main` branch's merge commit.
If all is successful it also deletes the `test-1.0.1` branch since it is no
longer needed.

Reflex also works to make hotfix branches as well.
```sh
reflex 1.0.2 --hotfix --repo git@github.com:brightmd/reflex.git
# Add hotfix changes to `test-1.0.2`
reflex 1.0.2 --close --repo git@github.com:brightmd/reflex.git
```

If you would like to no longer specify the `--repo` flag you may also set
the `REPO` environment variable.
```sh
export REPO='git@github.com:brightmd/reflex.git'
reflex 1.0.5 --release  # Automatically acts on the reflex repo
```

If working on a repo which does not use the default branch names for its
'production' (defaults to main) and 'development' (defaults to develop)
environments you must specify the different branches as the
`--production-branch` and `--development-branch` options on the command line
like so.
```sh
reflex --production-branch stable --development-branch development 1.2.0 --hotfix
```
