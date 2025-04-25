import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import matplotlib.pyplot as plt
import numpy as np

class AnimatorBase:
    def __init__(self, dpi=100):
        """
        Completely rebuilt animator base class using FigureCanvas directly
        instead of pyplot to avoid any state conflicts.
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
    
    def save_plot(self, filename='fig.png'):
        """Save the plot to a file"""
        # Draw the canvas to render the figure
        self.canvas.draw()
        
        # Save to file
        self.fig.savefig(filename, dpi=self.dpi, bbox_inches=None, 
                        pad_inches=0, transparent=True)
    
    def show_plot(self):
        """Display the plot using pyplot"""
        # Create a new pyplot figure for display
        display_fig = plt.figure(figsize=self.fig.get_size_inches(), dpi=self.dpi)
        display_ax = display_fig.add_axes([0, 0, 1, 1])
        
        # Get the figure as array
        img_array = self.get_plot()
        
        # Display the array as an image
        display_ax.imshow(img_array)
        display_ax.axis('off')
        
        # Show the plot
        plt.show()
        
        # Clean up
        plt.close(display_fig)
    
    def plot_setup(self):
        """Override in child class"""
        pass
    
    def update(self, custom_msg=None):
        """Override in child class"""
        pass


class AnimatorSimple(AnimatorBase):
    def __init__(self):
        super().__init__()
        self.plot_setup()
    
    def plot_setup(self):
        # Draw corner points in red
        self.ax.scatter(
            [0, 0, 4.1, 4.1], 
            [3.3-1.6, -1.6, 3.3-1.6, -1.6], 
            color=(1, 0, 0),  # RGB red
            s=100)
    
    def update(self):
        pass


if __name__ == "__main__":
    # Create the animator
    animator = AnimatorSimple()
    
    # Get the plot as array
    plot_array = animator.get_plot()
    print(f"Plot array shape: {plot_array.shape}")
    
    # Save to file
    animator.save_plot("rebuilt_plot.png")
    
    # Show interactively
    animator.show_plot()