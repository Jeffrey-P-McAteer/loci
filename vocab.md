
# Vocabulary

`loci` has several complex patterns which span many subprograms
and are responsible for non-obvious design decisions. They are
listed here as a point of reference.


 - `local client`: Any web-browser (embedded or otherwise) executing on the same hardware as a `ap-kernel*` program.
    - The desktop main window
    - The Android app screen
    - Any web browser on the same machine as the desktop main window

 - `remote client`: Any web-browser (embedded or otherwise) executing on a different machine than the one running a `ap-kernel*` programs.
    - An iPhone with `https://laptop-number-seven.local:7011/` open in one of the browser tabs
    - An iPhone with `https://laptop-number-seven.local:7011/` installed as a PWA
    - A windows PC with `https://laptop-number-seven.local:7011/` open in a browser tab
    - An android watch w/ `TODO kernel name` installed.




