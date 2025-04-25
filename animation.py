import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import numpy as np
import io
from PIL import Image

class AnimatorBase:
    def __init__(self, dpi=100):
        """
        Class used to create an animation that is later fused with the video.
        
        Useage:
        1. Create a child class 
        ```
        class Animator(AnimatorBase):
            def __init__(self):
                super().__init__()
            
            def plot_setup(self, ...):
                # add all elements that you want to plot

            def update(self, custom_msg):
                # update the plot with new data
                # customg_msg is a custom message that contains your desired data
        ```
        2. Pass the child class to the main function

        Refer to example for more clarity.

        Attention: 
        - This class ensures that the plot is not distorted in any way, neither here nor later
          during the video fusion process. Do not change the plot setup.
        - All units for plotting are in meters
        - The dpi setting can be used to change the resolution of the plot

        Ideas/Todo:
        - [ ] Add method to still show axis labels and ticks
        """
        # Close all existing pyplot figures to ensure clean state
        plt.close('all')
        
        # Set plot limits
        self.xmin, self.xmax = 0, 4.10
        self.ymin, self.ymax = -1.60, 1.70
        
        # Calculate aspect ratio
        x_range = self.xmax - self.xmin
        y_range = self.ymax - self.ymin
        aspect_ratio = y_range / x_range
        
        # Calculate figure dimensions
        width_inches = 10
        height_inches = width_inches * aspect_ratio
        self.width_px = int(width_inches * dpi)
        self.height_px = int(height_inches * dpi)
        self.dpi = dpi
        
        # Create a Figure (not using pyplot)
        self.fig = Figure(figsize=(width_inches, height_inches), dpi=dpi)
        
        # Create a canvas for the figure (required for rendering)
        self.canvas = FigureCanvasAgg(self.fig)
        
        # Create axes that fill the entire figure
        self.ax = self.fig.add_axes([0, 0, 1, 1], frameon=False)
        
        # Set the plot limits
        self.ax.set_xlim(self.xmin, self.xmax)
        self.ax.set_ylim(self.ymin, self.ymax)
        
        # Turn off axes
        self.ax.axis('off')
        
        # Disable autoscaling
        self.ax.autoscale(False)
        
        # Set transparent backgrounds
        self.fig.patch.set_alpha(0)
        self.ax.patch.set_alpha(0)
        
        # Add invisible corner points to force correct limits
        self._corner_points = self.ax.scatter(
            [self.xmin, self.xmax, self.xmin, self.xmax],
            [self.ymin, self.ymin, self.ymax, self.ymax],
            s=0, alpha=0)
    
    def get_plot(self):
        """Return the plot as a numpy array"""
        # Draw the canvas to render the figure
        self.canvas.draw()
        
        # Convert to numpy array
        plot_array = np.array(self.canvas.renderer.buffer_rgba())
        
        # Convert RGBA to RGB
        plot_array = plot_array[:, :, :3]
        
        return plot_array
    
    def plot_setup(self):
        """ Method for setting up the plot """
        pass
    
    def update(self):
        """ Method for updating the plot in animations """
        pass

