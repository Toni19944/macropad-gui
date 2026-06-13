"""Entry point: ``python -m macropad_gui`` / ``macropad-gui``."""

from .model import Config
from .ui.main_window import MainWindow


def main() -> None:
    window = MainWindow(Config.new(rows=3, columns=4, knobs=2, layer_count=3))
    window.mainloop()


if __name__ == "__main__":
    main()
