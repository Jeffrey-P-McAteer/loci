
# Usage: python app-data-tkeys/converter.py export-amalgamated
#        python app-data-tkeys/converter.py import-amalgamated
#        python app-data-tkeys/converter.py roundtrip
# 
# "export-amalgamated" exports to out/amalgamated-translations.cs
# "import-amalgamated" imports new values from out/amalgamated-translations.cs
# "roundtrip" exports and then imports data (sorting and replacing unicode with escape codes in the process, which cleans the data)


import os
import sys
import json
import csv
import glob
import re

def consistency_check(file, data):
  if any(c.isupper() for c in file):
    raise Exception('ERROR: Capital letter detected in file name, this is messy and wrecks portability across OSes which do not specify case in filesystems: {}'.format(file))

  if any(c.isspace() for c in file):
    raise Exception('ERROR: Whitespace detected in file name, this is messy and leads to copy/paste-caused errors! {}'.format(file))

  if data:
    # Check that all tkeys are lowercase alphanumeric plus "-", "_",
    for key in data.keys():
      
      if len(key) < 2:
        raise Exception('ERROR: tkey is too short; "{}" has length < 2 in file {}'.format(key, file))

      regex = r"^[a-z0-9_-]*$"
      if not re.match(regex, key):
        raise Exception('ERROR: tkey {} from {} does not match {}. Please use lower alphanumeric plus "-" and "_" to keep data tkey clean and readable!'.format(
          key, file, regex
        ))

def unique_tkey_consistency_check(translations):
  tkey_files = {} # {"abc": "abc.json"}
  for file, data in translations.items():
    for tkey in data.keys():
      if tkey in tkey_files:
        raise Exception('Duplicate tkey {} in both {} and {}'.format(
          tkey, tkey_files[tkey], file
        ))

def lookup_file_from_tkey(translations, search_tkey):
  for file, data in translations.items():
    for tkey in data.keys():
      if tkey == search_tkey:
        return file
  return 'misc-imported.json'

def read_json_data():
  # {"filename.json": {"abc": {"en": "A B C", "es": "..."}}}
  translations = {}
  for file in glob.glob('*.json'):

    consistency_check(file, None)

    if file in translations:
      raise Exception('Duplicate file: {}'.format(file))

    with open(file, 'r') as fd:
      translations[file] = json.load(fd)
      consistency_check(file, translations[file])

  unique_tkey_consistency_check(translations)

  return translations


def write_json_data(translations):
  unique_tkey_consistency_check(translations)
  all_lang_codes = get_lang_codes(translations)
  for file, contents in translations.items():
    consistency_check(file, contents)

    # Remove empty values:
    for tkey, tkey_dict in contents.items():
      for code in all_lang_codes:
        if len(tkey_dict[code]) < 1:
          tkey_dict.pop(code, None)
          print('WARNING: missing translation of "{}" from {} in language {}'.format(tkey, file, code))

    with open(file, 'w') as fd:
      json.dump(contents, fd, indent=2, sort_keys=True)


def get_lang_codes(translations):
  all_lang_codes = []
  for file, contents in translations.items():
    for tkey, tkey_dict in contents.items():
      for lang_code in tkey_dict.keys():
        if not lang_code in all_lang_codes:
          all_lang_codes.append(lang_code)
  
  all_lang_codes.sort()

  return all_lang_codes

def write_csv_data(translations, csv_file):
  unique_tkey_consistency_check(translations)

  all_lang_codes = get_lang_codes(translations)

  with open(csv_file, 'w') as fd:
    csv_writer = csv.writer(fd, quoting=csv.QUOTE_ALL)

    csv_writer.writerow(['TKEY'] + [code.upper() for code in all_lang_codes])

    for file, contents in translations.items():
      consistency_check(file, contents)

      for tkey, tkey_dict in contents.items():
        
        # Ensure dictionaries have _something_ for all languages
        for code in all_lang_codes:
          if not code in tkey_dict:
            #tkey_dict[code] = 'TODO translate "{}" from "{}" into lang "{}"'.format(tkey, file, code)
            tkey_dict[code] = ''

        csv_writer.writerow([tkey] + [tkey_dict[code] for code in all_lang_codes])


def update_from_csv_data(translations, csv_file):

  with open(csv_file, 'r') as fd:
    csv_reader = csv.reader(fd)

    all_lang_codes = None

    for row in csv_reader:
      if not all_lang_codes:
        # First row
        all_lang_codes = [code.lower() for code in row[1:]]
      else:
        # remaining rows
        tkey = row[0]
        translation_values = row[1:]

        if len(translation_values) < len(all_lang_codes):
          raise Exception('Missing translation values for tkey {}: got {} expected {}'.format(tkey, len(translation_values), len(all_lang_codes)))

        translation_json_file = lookup_file_from_tkey(translations, tkey)
        
        if not (translation_json_file in translations):
          translations[translation_json_file] = {}

        if not (tkey in translations[translation_json_file]):
          translations[translation_json_file][tkey] = {}

        for i, code in enumerate(all_lang_codes):
          translations[translation_json_file][tkey][code] = translation_values[i]


  return translations


def main(args=sys.argv):
  app_data_tkeys_dir = os.path.dirname(os.path.realpath(__file__))
  os.chdir(app_data_tkeys_dir)

  amalgamated_translations_csv = os.path.realpath(os.path.join('..', 'out', 'amalgamated-translations.csv'))

  if 'export-amalgamated' in args or 'export' in args:
    write_csv_data(read_json_data(), amalgamated_translations_csv)
    print('Wrote translation data to {}'.format(amalgamated_translations_csv))

  elif 'import-amalgamated' in args or 'import' in args:
    write_json_data(update_from_csv_data(read_json_data(), amalgamated_translations_csv))
    print('Imported translation data from {}'.format(amalgamated_translations_csv))

  elif 'roundtrip' in args:
    main(['export-amalgamated'])
    main(['import-amalgamated'])

  else:
    print('''
Usage: python app-data-tkeys/converter.py export-amalgamated
       python app-data-tkeys/converter.py import-amalgamated
       python app-data-tkeys/converter.py roundtrip

"export-amalgamated" exports to out/amalgamated-translations.cs
"import-amalgamated" imports new values from out/amalgamated-translations.cs
"roundtrip" exports and then imports data (sorting and replacing unicode with escape codes in the process, which cleans the data)

''')


if __name__ == '__main__':
  main()


