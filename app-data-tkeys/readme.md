
# App data: tkeys

This directory holds `.json` files formatted as follows:

```
{
  "hello_world": {
    "en": "Hello World!",
    "es": "¡Hola Mundo!",
    "fr": "Bonjour le monde!"
  },
  "welcome_user": {
    "en": "Welcome, User",
    "es": "Bienvenido usuario",
    "fr": "Bienvenue, utilisateur"
  }
}
```

Notice a few gaps in our translation model: there is no good way to specify gender-specific translations.
"Bienvenido usuario" and "Bienvenida usuaria" are both valid translations of "Welcome, User", and if programmers
need both they must create 2 seperate tkeys (eg "welcome_user_m" and "welcome_user_f") and decide using their own
subprogram's logic.


# `converter.py`

The converter script accepts three arguments: "export-amalgamated", "import-amalgamated", and "roundtrip".

`python app-data-tkeys/converter.py export-amalgamated` will take all `*.json` files under `app-data-tkeys/` and produce a single
file `out/amalgamated-translations.csv` formatted like so:

```,
TKEY,EN,ES,FR,
hello_world,Hello World!,¡Hola Mundo!,Bonjour le monde!
welcome_user,"Welcome, User",Bienvenido usuario,"Bienvenue, utilisateur"
```

`python app-data-tkeys/converter.py import-amalgamated` will read the file `out/amalgamated-translations.csv` and append 
new translation data to the file `misc-imported.json` as well as update existing tkey-langcode values in the json files they are defined in.
Removing entries MUST be done by modifying `*.json` files directly.


`python app-data-tkeys/converter.py roundtrip` will perform both steps above, which sorts tkeys and translates unicode characters into escape sequences,
making our predefined translation data cleaner and less likely to break IDEs like Eclipse and IntelliJ.



