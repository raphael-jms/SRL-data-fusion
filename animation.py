import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

class Animator:
    def __init__(self):
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
        self.fig = plt.figure(figsize=(width_inches, height_inches))
        
        # Create axes that fill the entire figure
        self.ax = plt.axes([0, 0, 1, 1], frameon=False)
        
        # Set the data limits
        self.ax.set_xlim(self.xmin, self.xmax)
        self.ax.set_ylim(self.ymin, self.ymax)
        
        # Don't set aspect='equal' as it will distort the plot
        # Instead, we've already accounted for aspect ratio in the figure size
        
        # Disable axes completely
        self.ax.get_xaxis().set_visible(False)
        self.ax.get_yaxis().set_visible(False)
        
        # Turn off all padding
        plt.autoscale(tight=True)
        
        # Make figure and axes backgrounds transparent
        for item in [self.fig, self.ax]:
            item.patch.set_visible(False)
        
        # Example data points
        self.ax.scatter(
            [0, 0, 4.1, 4.1], 
            [3.3-1.6, -1.6, 3.3-1.6, -1.6], 
            c='r', s=100)
    
    def get_plot(self):
        """ Return the plot as numpy array """
        self.fig.canvas.draw()
        plot_array = np.frombuffer(self.fig.canvas.tostring_rgb(), dtype=np.uint8)
        plot_array = plot_array.reshape(self.fig.canvas.get_width_height()[::-1] + (3,))
        return plot_array

    def save_plot(self, filename='fig.png'):
        """ Save the plot to a file """
        plt.savefig(filename, bbox_inches=None, pad_inches=0)
    
    def show_plot(self):
        """ Display the plot """
        plt.show()
    
    def update(self):
        """ Method for updating the plot in animations """
        pass

if __name__ == "__main__":
    ani = Animator()
    ani_img = ani.get_plot()
    plt.imshow(ani_img)
    plt.show()