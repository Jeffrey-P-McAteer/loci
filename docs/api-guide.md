
# Loci API Guide

Loci extracts 3rd-party programs (such as GeoServer and RTL-SDR receivers) to
a directory referred to as the "eapp" directory (extra applications).

Developers may add their own programs to be executed in this directory.

On windows systems the directory is `%LocalAppData%\DeVil-Tech\Loci\eapp\`

On linux systems the directory is `~/.cache/Loci/eapp/`

Under the eapp directory create a directory named `user-programs`.


TODO document how file extensions affect the enviroment variables set (CLASSPATH, PYTHONPATH)
so that Loci libraries are importable.


