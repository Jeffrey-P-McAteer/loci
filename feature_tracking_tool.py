
# This script reports on the contents of "features.json"
# in sub-directories containing sub-programs.
# The goal is to be able to track partial progress on
# features by specifying feature goals and requirements
# before writing tests and implementation.

# You may pass "todo", "completed", or "began" to change which features are printed.
# This is useful for planning work or quickly reporting progress.

# passing "next" will print the highest-priority "began" feature,
# falling back to the highest-priority "todo" feature.

import json
import pathlib
import sys
import os
import re
import datetime

def find_features_files(base_dir='.', recursive_steps=3):
  if recursive_steps < 1:
    return
  
  for name in os.listdir(base_dir):
    # Ignore build dirs for performance
    if name in ['build', 'out', 'target', 'bin']:
      continue

    name = os.path.join(base_dir, name)

    if name.endswith('features.json'):
      yield name

    elif os.path.isdir(name):
      yield from find_features_files(base_dir=name, recursive_steps=recursive_steps-1)

  # This is SLOW
  # for file in pathlib.Path('.').rglob('features.json'):
  #   yield file


def remove_comments_from_json(json_str):
  # everything from "//" to "\n" or from "/*" to "*/"
  json_str = re.sub('//.*?\n|/\*.*?\*/', '', json_str, flags=re.S)
  # Remove trailing commas '{"name": "value",}'
  json_str = re.sub(',[ \t\r\n]+}', '}', json_str)
  json_str = re.sub(',[ \t\r\n]+]', ']', json_str)
  return json_str

def check_req_keys(feature):
  if not 'priority' in feature:
    print('ERROR: feature does not have required key "priority". This must be a unique number used to sort features by relative importance.')
    sys.exit(5)

  if not 'name' in feature:
    print('ERROR: feature does not have required key "name".')
    sys.exit(5)

# returns {"./subdir/": [{"name":...}, {}, {} ... ], "./subdir2": [{}, {}...] ... }
def parse_all_features(print_warnings=True):
  
  all_features = {}

  for file in find_features_files():
    feature_list = []
    with open(file, 'r') as fd:
      contents = fd.read()
      
      if not contents or len(contents) < 2:
        if print_warnings: print('WARNING: {} is empty!'.format(file))
        continue

      feature_list = json.loads(remove_comments_from_json(contents))

    if not isinstance(feature_list, list):
      if print_warnings: print('WARNING: {} is not a JSON list!'.format(file))
      continue
    
    proj_dir = os.path.dirname(file)
    # print('=== {} ==='.format(proj_dir))

    sorted_features = sorted(feature_list, key=lambda x: x['priority'])

    all_features[proj_dir] = sorted_features

    last_feature_priority = -1
    for feature in sorted_features:
      check_req_keys(feature)
      if feature['priority'] == last_feature_priority:
        if print_warnings: print('ERROR: feature "{}" has duplicated priority number! Ensure priority numbers are unique for all features.')
        sys.exit(5)
      last_feature_priority = feature['priority']

  # Finally dump warnings for directories which we EXPECT to have features.json but do not
  def expect_dir_to_have_features_json(dirname):
    if not os.path.exists(os.path.join(dirname, 'features.json')):
      print('WARNING: expected features.json in {} but did not find any!'.format(dirname))

  for name in os.listdir('app-subprograms'):
    expect_dir_to_have_features_json(os.path.join('app-subprograms', name))

  misc_expected_dirs = [
    'app-lib', 'app-kernel-desktop', 'app-kernel-android',
  ]
  for name in misc_expected_dirs:
    expect_dir_to_have_features_json(name)

  return all_features

def print_feature(feature):
  # Print this feature
  indent = '    '
  print('{}: {}: '.format(feature['priority'], feature['name']))

  if 'completed' in feature:
    print('{}COMPLETED {}'.format(indent, feature['completed']))
  elif 'began' in feature:
    print('{}BEGAN {}'.format(indent, feature['began']))
  else:
    print('{}TODO'.format(indent))

  if 'comments' in feature:
    print('{}{}'.format(indent, feature['comments']))

  print('')

def main(args=sys.argv):

  todos_only = 'todo' in args
  completed_only = 'completed' in args
  began_only = 'began' in args

  print_next = 'next' in args

  if print_next:
    highest_priority = 999999999
    best_feature = None
    best_feature_subdir = None
    # Search for "began" features
    for subdir, features in parse_all_features().items():
      for feature in features:
        if 'began' in feature and feature['priority'] < highest_priority:
          highest_priority = feature['priority']
          best_feature = feature
          best_feature_subdir = subdir

    if not best_feature:
      # We didn't find in-progress, move on to "todo" search
      for feature in features:
        if not ('began' in feature or 'completed' in feature) and feature['priority'] < highest_priority:
          highest_priority = feature['priority']
          best_feature = feature
          best_feature_subdir = subdir

    # Finally print everything
    if not best_feature:
      print('No next feature to implement!')
    else:
      print('=== {} ==='.format(best_feature_subdir))
      print_feature(best_feature)

  else:
    for subdir, features in parse_all_features().items():
      
      print('=== {} ==='.format(subdir))

      for feature in features:
        # Skip printing according to args from user
        if todos_only and 'completed' in feature:
          continue
        if began_only and not ('began' in feature):
          continue
        if completed_only and not ('completed' in feature):
          continue

        print_feature(feature)



if __name__ == '__main__':
  main()


