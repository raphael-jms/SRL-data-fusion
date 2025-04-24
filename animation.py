import matplotlib.pyplot as plt
import numpy as np

class Animator:
    def __init__(self):
        self.plot_limits = [0, 4.10, -1.60, 1.70]  # [xmin, xmax, ymin, ymax]
        self.fig, self.ax = plt.subplots(figsize=(10, 10))
        """
        dpi	float, default: rcParams["figure.dpi"] (default: 100.0)	resolution of the figure in dot per inch.
        """
        self.ax.set_xlim(self.plot_limits[0], self.plot_limits[1])
        self.ax.set_ylim(self.plot_limits[2], self.plot_limits[3])
        self.ax.set_aspect('equal')
        self.ax.axis('off')

        self.ax.plot([0,1,2,3], [0,1,4,3], 'r-')  # Example plot
    
    def get_plot(self):
        """ Return the plot as numpy array """
        self.fig.canvas.draw()
        plot_array = np.frombuffer(self.fig.canvas.tostring_rgb(), dtype=np.uint8)
        plot_array = plot_array.reshape(self.fig.canvas.get_width_height()[::-1] + (3,))
        return plot_array

    def update(self):
        pass