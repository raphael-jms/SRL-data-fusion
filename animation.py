import matplotlib as mpl
import matplotlib.pyplot as plt
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
        # Set plot limits
        self.xmin, self.xmax = 0, 4.10
        self.ymin, self.ymax = -1.60, 1.70
        
        # Calculate the aspect ratio based on the data range
        x_range = self.xmax - self.xmin
        y_range = self.ymax - self.ymin
        aspect_ratio = y_range / x_range
        
        # Remove padding
        mpl.rcParams['savefig.pad_inches'] = 0
        
        # Create figure with appropriate size to match data aspect ratio
        # Width is set to 10 inches, height is adjusted according to aspect ratio
        width_inches = 10
        height_inches = width_inches * aspect_ratio

        self.width_px = int(width_inches * dpi)
        self.height_px = int(height_inches * dpi)
        self.dpi = dpi

        self.fig = plt.figure(figsize=(width_inches, height_inches), dpi=dpi)
        
        # Create axes that fill the entire figure
        self.ax = plt.axes([0, 0, 1, 1], frameon=False)
        
        # # Set the data limits
        # self.ax.set_xlim(self.xmin, self.xmax)
        # self.ax.set_ylim(self.ymin, self.ymax)
        
        # Don't set aspect='equal' as it will distort the plot
        # Instead, we've already accounted for aspect ratio in the figure size
        
        # # Disable axes completely
        # self.ax.get_xaxis().set_visible(False)
        # self.ax.get_yaxis().set_visible(False)
        
        # # Turn off all padding
        # plt.autoscale(tight=True)
        # self.ax.autoscale(False)
        
        # # Make figure and axes backgrounds transparent
        # for item in [self.fig, self.ax]:
        #     item.patch.set_visible(False)
        
        self.plot_setup()
    
    def get_plot_old(self):
        """ Return the plot as numpy array """
        self.fig.canvas.draw()
        plot_array = np.frombuffer(self.fig.canvas.tostring_rgb(), dtype=np.uint8)
        plot_array = plot_array.reshape(self.fig.canvas.get_width_height()[::-1] + (3,))
        return plot_array

    def get_plot_old2(self):
        # Force a draw of the figure to ensure it's rendered
        self.fig.canvas.draw()
        
        # Get the renderer and draw again to a fresh canvas
        renderer = self.fig.canvas.get_renderer()
        self.fig.draw(renderer)
        
        # Get the RGB buffer
        plot_array = np.frombuffer(self.fig.canvas.tostring_rgb(), dtype=np.uint8)
        plot_array = plot_array.reshape(self.fig.canvas.get_width_height()[::-1] + (3,))
        return plot_array

    def get_plot(self):
        """Return the plot as numpy array using system renderer via savefig"""
        # Create in-memory binary stream
        buf = io.BytesIO()
        
        # Save figure to the buffer using the system renderer
        self.fig.savefig(buf, format='png', dpi=self.dpi, 
                        bbox_inches=None, pad_inches=0, 
                        facecolor='none', transparent=True)
        buf.seek(0)
        
        # Load the image from buffer using PIL
        image = Image.open(buf)
        
        # Convert PIL image to numpy array
        plot_array = np.array(image.convert('RGB'))
        
        # Close the buffer
        buf.close()
        
        return plot_array

    def plot_setup(self):
        """ Method for setting up the plot """
        pass
    
    def update(self):
        """ Method for updating the plot in animations """
        pass

