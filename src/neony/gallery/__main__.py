"""Console / ``python -m neony.gallery`` entry point.

Uses an absolute import (not ``from .assemble``) so Nuitka can compile
this file as the standalone entry: ``nuitka src/neony/gallery/__main__.py``
resolves the package via the installed ``neony`` on sys.path.
"""

from neony.gallery.assemble import main

if __name__ == "__main__":
    main()
