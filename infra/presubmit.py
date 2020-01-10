#!/usr/bin/env python3
# Copyright 2020 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
################################################################################
"""Check code for common issues before submitting."""

import argparse
import itertools
import os
import subprocess
import sys
import yaml


_SRC_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _is_project_file(actual_path, expected_filename):
  """Returns True if |expected_filename| a file that exists in |actual_path| a
  path in projects/."""
  if os.path.basename(actual_path) != expected_filename:
    return False

  if os.path.basename(os.path.dirname(
    os.path.dirname(actual_path))) != 'projects':
    return False

  return os.path.exists(actual_path)


def _check_one_lib_fuzzing_engine(build_sh_file):
  """Returns False if |build_sh_file| contains -lFuzzingEngine.
  This is deprecated behavior. $LIB_FUZZING_ENGINE should be used instead
  so that -fsanitize=fuzzer is used."""
  if not _is_project_file(build_sh_file, 'build.sh'):
    return True

  with open(build_sh_file) as build_sh:
    build_sh_lines = build_sh.readlines()
  for line_num, line in enumerate(build_sh_lines):
    uncommented_code = line.split('#')[0]
    if '-lFuzzingEngine' in uncommented_code:
      print('''Error: build.sh contains -lFuzzingEngine on line: {0}.
Please use $LIB_FUZZING_ENGINE.'''.format(line_num))
      return False
  return True


def check_lib_fuzzing_engine(paths):
  """Call _check_one_lib_fuzzing_engine on each path in |paths|. Return True if
  the result of every call is True."""
  return all(_check_one_lib_fuzzing_engine(path) for path in paths)


class ProjectYamlChecker:
  """Checks for a project.yaml file."""

  # Sections in a project.yaml and the constant values that they are allowed
  # to have.
  SECTIONS_AND_CONSTANTS = {
    'sanitizers': ['address', 'none', 'memory', 'address'],
    'architectures': ['i386', 'x86_64'],
    'engines': ['afl', 'libfuzzer', 'honggfuzz']
  }

  # Note: this list must be updated when we allow new sections.
  VALID_SECTION_NAMES = [
    'homepage', 'primary_contact', 'auto_ccs', 'sanitizers',
    'architectures', 'disabled'
  ]

  # Note that some projects like boost only have auto-ccs. However, forgetting
  # primary contact is probably a mistake.
  REQUIRED_SECTIONS = ['primary_contact']

  def __init__(self, project_yaml_filename):
    self.project_yaml_filename = project_yaml_filename
    with open(project_yaml_filename) as file_handle:
      self.project_yaml = yaml.safe_load(file_handle)

    self.success = True

    self.checks = [
      self.check_project_yaml_constants, self.check_required_sections,
      self.check_valid_section_names, self.check_valid_emails
    ]

  def do_checks(self):
    """Do all project.yaml checks. Return True if they pass."""
    if self.is_disabled():
      return True
    for check_function in self.checks:
      check_function()
    return self.success

  def is_disabled(self):
    """Is this project disabled."""
    return self.project_yaml.get('disabled', False)

  def print_error_message(self, message, *args):
    """Print an error message and set self.success to False."""
    self.success = False
    message = message % args
    print('Error in %s: %s' % (self.project_yaml_filename, message))

  def check_project_yaml_constants(self):
    """Check that certain sections only have certain constant values."""
    for section, constants in self.SECTIONS_AND_CONSTANTS.items():
      if section not in self.project_yaml:
        continue
      section_contents = self.project_yaml[section]
      for constant in section_contents:
        if constant not in section_contents:
          self.print_error_message('%s not one of %s', constant,
                       constants)

  def check_valid_section_names(self):
    """Check that only valid sections are included."""
    for name in self.project_yaml:
      if name not in self.VALID_SECTION_NAMES:
        self.print_error_message('%s not a valid section name (%s)',
                     name, self.VALID_SECTION_NAMES)

  def check_required_sections(self):
    """Check that all required sections are present."""
    for section in self.REQUIRED_SECTIONS:
      if section not in self.project_yaml:
        self.print_error_message('No %s section.', section)

  def check_valid_emails(self):
    """Check that emails are valid looking."""
    # Get email addresses.
    email_addresses = []
    for section in ['auto_ccs', 'primay_contact']:
      email_addresses.extend(self.project_yaml.get(section, []))

    # Sanity check them.
    for email_address in email_addresses:
      if not ('@' in email_address and '.' in email_address):
        self.print_error_message(
          '%s is an invalid email address.', email_address)


def _check_one_project_yaml(project_yaml_filename):
  """Do checks on the project.yaml file."""
  if not _is_project_file(project_yaml_filename, 'project.yaml'):
    return True

  checker = ProjectYamlChecker(project_yaml_filename)
  return checker.do_checks()


def check_project_yaml(paths):
  """Call _check_one_project_yaml on each path in |paths|. Return True if
  the result of every call is True."""
  return all(_check_one_project_yaml(path) for path in paths)


def do_checks(changed_files):
  """Return False if any presubmit check fails."""
  success = True

  checks = [check_license, yapf, lint,
            check_project_yaml, check_lib_fuzzing_engine]
  if not all(check(changed_files) for check in checks):
    success = False

  return success


_CHECK_LICENSE_FILENAMES = ['Dockerfile']
_CHECK_LICENSE_EXTENSIONS = [
    '.bash',
    '.c',
    '.cc',
    '.cpp',
    '.css',
    '.h',
    '.htm',
    '.html',
    '.js',
    '.proto',
    '.py',
    '.sh',
    '.yaml',
]
_LICENSE_STRING = 'http://www.apache.org/licenses/LICENSE-2.0'


def check_license(paths):
  """Validate license header."""
  if not paths:
    return True

  success = True
  for path in paths:
    filename = os.path.basename(path)
    extension = os.path.splitext(path)[1]
    if (filename not in _CHECK_LICENSE_FILENAMES and
        extension not in _CHECK_LICENSE_EXTENSIONS):
      continue

    with open(path) as file_handle:
      if _LICENSE_STRING not in file_handle.read():
        print('Missing license header in file %s.' % str(path))
        success = False

  return success


def bool_to_returncode(success):
  """Return 0 if |success|. Otherwise return 1."""
  if success:
    print('Success.')
    return 0

  print('Failed.')
  return 1

def is_python(path):
  """Returns True if |path| ends in .py."""
  return path.suffix == '.py'


def lint(paths):
  """Run python's linter on |paths| if it is a python file. Return False if it
  fails linting."""
  paths = [path for path in paths if is_python(path)]
  paths = filter_migrations(paths)
  if not paths:
    return True

  command = ['python3', '-m', 'pylint', '-j', '0']
  command.extend(paths)
  returncode = subprocess.run(command, check=False).returncode
  return returncode == 0


def yapf(paths, validate):
  """Do yapf on |path| if it is Python file. Only validates format if
  |validate| otherwise, formats the file. Returns False if validation
  or formatting fails."""
  paths = [path for path in paths if is_python(path)]
  if not paths:
    return True

  validate_argument = '-d' if validate else '-i'
  command = ['yapf', validate_argument, '-p']
  command.extend(paths)
  returncode = subprocess.run(command, check=False).returncode
  return returncode == 0


def get_changed_files():
  """Return a list of absolute paths of files changed in this git branch."""
  diff_command = ['git', 'diff', '--name-only', 'FETCH_HEAD']
  return [
      os.path.abspath(path)
      for path in subprocess.check_output(diff_command).decode().splitlines()
      if os.path.isfile(path)
  ]


def main():
  """Check changes on a branch for common issues before submitting."""
  # Get program arguments.
  parser = argparse.ArgumentParser(
      description='Presubmit script for fuzzer-benchmarks.')
  parser.add_argument('command',
                      choices=['format', 'lint', 'license'],
                      nargs='?')
  args = parser.parse_args()

  changed_files = get_changed_files()
  print(changed_files)

  # Do one specific check if the user asked for it.
  if args.command == 'format':
    success = yapf(changed_files, False)
    return bool_to_returncode(success)

  if args.command == 'lint':
    success = lint(changed_files)
    return bool_to_returncode(success)

  if args.command == 'license':
    success = check_license(changed_files, False)
    return bool_to_returncode(success)

  # Otherwise, do all of them.
  success = do_checks(changed_files)
  return bool_to_returncode(success)


if __name__ == '__main__':
  main()
