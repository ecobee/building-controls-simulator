# Table of contents

- [Contributing to Building Controls Simulator](#contributing-to-Building-Controls-Simulator)
- [Development Setup](#Development-Setup)
- [Codebase structure](#codebase-structure)
- [Unit testing](#unit-testing)
- [Writing documentation](#writing-documentation)
  - [Building documentation](#building-documentation)
  - [Previewing documentation changes](#previewing-changes)
  - [Submitting documentation changes for review](#submitting-changes-for-review)
  - [Adding documentation tests](#adding-documentation-tests)

## Contributing to Building Controls Simulator

If you are interested in contributing to the Building Controls Simulator (BCS for short) project, your contributions will fall
into two categories:

1. You want to propose a new feature and implement it.
    - Post about your intended feature, and we shall discuss the design and
    implementation. Once we agree that the plan looks good, go ahead and implement it.
2. You want to implement a feature or bug-fix for an outstanding issue.
    - Search for your issue here: https://github.com/ecobee/building-controls-simulator/issues
    - Pick an issue and comment on the task that you want to work on this feature.
    - If you need more context on a particular issue, please ask and we shall provide.

Once you finish implementing a feature or bug-fix, please send a Pull Request to
https://github.com/ecobee/building-controls-simulator

## Development setup

To develop Building Controls Simulator on your machine, here are some tips:

1. Clone a copy of the Building Controls Simulator repo from source:

```bash
git clone https://github.com/ecobee/building-controls-simulator
cd building-controls-simulator
```

2. Build docker image:

The docker container provides EnergyPlus version management and isolated cross-platform development environment

```bash
make build-docker
```

3. run docker container with edittable library files mounted:

```bash
make run
```

## Codebase structure

* [src](src) - Core library files
* [tests/python](tests/python) - Unittests
* [notebooks](noteoboks) - Jupyter notebooks used for interaxctive development, testing, and debugging

## Unit testing

Tests are located under `test/`. Run the entire test suite with:

```bash
python -m pytest
```

or run individual test suites, test files, or individual tests. For example:

```bash
python -m pytest tests/python/IDFPreprocessor/test_IDFPreprocessor.py::TestIDFPreprocessor::test_preprocess
```

Ideally all new code will be accompanied by unittests written by someone who has 
full context of those changes. Usually this would be the person implementing the 
changes. However, we appreciate WIP branches and PRs to illustrate ideas without 
working unit tests.

## Writing documentation
For documenation BCS uses [Sphinx](https://www.sphinx-doc.org/en/master/) with 
[Google style](http://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html)
for formatting docstrings. Length of line inside docstrings block must be limited to 80 characters to
fit into Jupyter documentation popups.

### Building documentation

Generate the documentation HTML files. The generated files will be in `docs/build/html`.

```bash
cd docs
make html
```

#### Previewing documentation changes

To view HTML files locally, you can open the files in your web browser. For example,
navigate to `$PACKAGE_DIR/docs/build/html/index.html` in a web browser.

If you are developing on a remote machine, you can set up an SSH tunnel so that
you can access the HTTP server on the remote machine from your local machine. To map
remote port 8000 to local port 8000, use either of the following commands.

```bash
# For SSH
ssh my_machine -L 8000:my_machine:8000

# For Eternal Terminal
et my_machine -t="8000:8000"
```

Then navigate to `localhost:8000` in your web browser.

#### Submitting documentation changes for review

It is helpful when submitting a PR that changes the docs to provide a rendered
version of the result. If your change is small, you can add a screenshot of the
changed docs to your PR.

If your change to the docs is large and affects multiple pages, you can host
the docs yourself with the following steps, then add a link to the output in your
PR. These instructions use GitHub pages to host the docs
you have built. To do so, follow [these steps](https://guides.github.com/features/pages/)
to make a repo to host your changed documentation.

GitHub pages expects to be hosting a Jekyll generated website which does not work
well with the static resource paths used in the Sphinx documentation. To get around
this, you must add an empty file called `.nojekyll` to your repo.

```bash
cd your_github_pages_repo
touch .nojekyll
git add .
git commit
git push
```

Then, copy built documentation and push the changes:

```bash
cd your_github_pages_repo
cp -r $PACKAGE_DIR/docs/build/html/* .
git add .
git commit
git push
```

Then you should be able to see the changes at your_github_username.github.com/your_github_pages_repo.


#### Adding documentation tests

It is easy for code snippets in docstrings and `.rst` files to get out of date. The docs
build includes the [Sphinx Doctest Extension](https://www.sphinx-doc.org/en/master/usage/extensions/doctest.html),
which can run code in documentation as a unit test. To use the extension, use
the `.. testcode::` directive in your `.rst` and docstrings.

To manually run these tests, follow steps 1 and 2 above, then run:

```bash
cd docs
make doctest
```
