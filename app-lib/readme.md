
# App Lib

This library is designed to hold functionality common to all subprograms and parts
of the app-kernel.

Functionality provided:

 - Discover app _install directory_ and _app root_ (a shared writeable directory for subprograms to store large files in)

 - Create/Open/Read/Write to shared sqlite databases given a db name
    - Used to share structured data between subprograms and to remember structured data across app restarts
    - Only one subprogram should create database schemas! (TODO add check in btool/ to fail build if we detect 2 subprograms initializing the same db)

 - Open/Read/Write to shared memory given a shared memory filename
    - subprograms must document memory formats __explicitly__ and all consumers of the memory must respect that API.
      This capability is designed for 2+ subprograms which need to share partially-structured data not saved in a db with as little latency as possible,
      such as shared graphics buffers or signal passing.

 - Check environment for license (.txt file under _app_root_ or env var) and verify it was signed by us and is valid for the current date/time.

 - Utility functions to inspect environment variables for changing common behaviors:
    - Verbosity level as an integer (0=only OS outputs (segfaults etc), 1=normal logs (3rd-party library outputs), 2=many logs (our own eprintln!() calls))
    - Determine enabled subprograms given name (app-kernel mostly cares about this but subprograms can also learn what has been loaded)



This library should be compiled in to the sub-program such that the sub-program
is built as a single library. This lib will not change so frequently that sub-programs
need to worry about following new versions.


