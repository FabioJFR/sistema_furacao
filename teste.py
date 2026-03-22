import pyvista as pv
import numpy as np

pv.global_theme.interactive = True

plotter = pv.Plotter()
plotter.show(interactive_update=True, auto_close=False)

pts = np.array([[0,0,0],[10,0,-10],[20,5,-20]])

plotter.add_lines(pts, width=5, connected=True)

while True:
    plotter.update()