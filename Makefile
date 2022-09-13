#!/usr/bin/make

# Useful variables:
# gitroot	Full path of the top folder in the git checkout
# repo		Last element of the git root folder path
# PROJECT_NAME	Defaults to `repo` but override to use a different name for pyenv, docker container etc.
# project	Relative path to the project folder within the git checkout.
# python_version	Base Python version for venv
# packages	Names of Python package folders (excluding migrations/ if it exists)

gitroot = ${shell git rev-parse --show-toplevel}
repo = ${notdir ${gitroot}}
PROJECT_NAME ?= ${repo}
project = ${dir ${shell git ls-files --full-name ${firstword ${MAKEFILE_LIST}}}}
python_version = 3.9.5
ignore_packages ?= migrations/
packages = ${filter-out ${ignore_packages},${dir ${wildcard */__init__.py}}}

SITE_PACKAGES := $(shell pip show pip | grep '^Location' | grep '${PROJECT_NAME}' | cut -f2 -d':')
ifeq (,${SITE_PACKAGES})
SITE_PACKAGES := site-packages-not-installed
endif

COMMON_MAKEFILE_DIR := $(dir $(lastword $(MAKEFILE_LIST)))

.DEFAULT_GOAL := help

-include ${MAKEFILE_INCLUDES}

.PHONY: help pyenv install init-pyenv rm-pyenv lint

help:    ## Shows documented makefile targets.
	+@printf "Usage:\n\tmake [options] target ...\n\nMake targets:\n"
	+@echo "$$(grep -hE '^\S+:.*##' $(MAKEFILE_LIST) | sort | sed -e 's/:.*##\s*/:/' -e 's/\(.*\):\(.*\)/\\x1b[36m\1\\x1b[m:\2/' | column -c2 -t -s :)"
	+@echo "\nTox environments also available as make targets:"
	+@tox -av | grep -vE '^using tox'

poetry.lock: pyproject.toml
	poetry install -v && touch $@

.python-version:
	make rm-pyenv
	pyenv virtualenv $(python_version) $(PROJECT_NAME)
	pyenv local $(PROJECT_NAME)

init-pyenv: .python-version install

rm-pyenv:
	pyenv local --unset
	pyenv uninstall -f $(PROJECT_NAME)
	touch -t 1901010000.00 -c -m poetry.lock

pyenv: ## Creates a local Python virtual environment using pyenv, installs all packages, and makes it automatically active within the project directory tree. This virtual environment is not a pre-requisite for running tests.
pyenv:  .python-version

pyenv: poetry.lock

clean:   ## Removes the pyenv environment and all tox environments.
clean: rm-pyenv
	rm -rf .tox *.egg-info

# Pre-commit hooks. Targets only installed if there is a pre-commit configuration.
ifneq (,$(wildcard .pre-commit-config.yaml))

${gitroot}/.git/hooks/pre-commit: .pre-commit-config.yaml
	pre-commit install

install: ${gitroot}/.git/hooks/pre-commit
endif

TOX_TARGETS=$(shell tox -a | grep -v "provision")
${TOX_TARGETS}: install
	tox -e $@

test: ## Equivalent to running tox with no arguments. This should be the normal command used to run unit tests from the command line.
test: install
	tox
