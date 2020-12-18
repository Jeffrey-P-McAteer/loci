
# Loci Docs

The `./docs/` directory holds writeup about Loci's
public interface.

Graphs are generally written in the [PlantUML language](https://plantuml.com/)
and documents are in markdown, but advanced formats like LaTeX
are find so long as you can compile them into something readable
in a web browser using `build.py`.

A directory of web-documents can be built
by running:

```bash
python -m docs.build
# To open your web browser to the built directory:
python -m docs.build open
```

This directory may also be pushed to Github Pages:

```bash
python -m docs.build publish
```





