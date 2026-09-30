"""Keep every plot on the same Qt binding as the PySide6 application."""
import os

# Override machine-specific preferences before pyqtgraph selects its binding.
os.environ['PYQTGRAPH_QT_LIB'] = 'PySide6'

import pyqtgraph as pg

if pg.Qt.QT_LIB != 'PySide6':
    raise RuntimeError(
        'pyqtgraph was already loaded with a different Qt binding. '
        'Restart Python and launch main.py in a fresh process.'
    )
