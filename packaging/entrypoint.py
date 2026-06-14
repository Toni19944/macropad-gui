"""PyInstaller entry-point shim for the frozen macropad-gui build.

PyInstaller runs the analyzed script as the top-level ``__main__`` module with
no package context, which breaks the relative imports inside
``macropad_gui/__main__.py``. This shim imports the package with an *absolute*
import so ``macropad_gui.__main__`` is loaded as a proper submodule (its
``from .model import ...`` relative imports then resolve), and calls ``main()``.

It exists only for packaging; running from source still uses
``python -m macropad_gui`` and never touches this file.
"""

from macropad_gui.__main__ import main

if __name__ == "__main__":
    main()
