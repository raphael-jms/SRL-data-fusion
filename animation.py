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
        
        Usage:
        1. Create a child class 
        ```
        class Animator(AnimatorBase):
            def __init__(self):
                super().__init__()
            
            def plot_setup(self, ...):
                # add all elements that you want to plot
                # store artists that will be animated in self._animated_artists list
                self._animated_artists.append(artist)

            def update(self, custom_msg):
                # update the plot with new data
                # custom_msg is a custom message that contains your desired data
                # update your artists and call self._blit_manager.update()
        ```
        2. Pass the child class to the main function

        Refer to example for more clarity.

        Attention: 
        - This class ensures that the plot is not distorted in any way, neither here nor later
          during the video fusion process. Do not change the plot setup.
        - All units for plotting are in meters
        - The dpi setting can be used to change the resolution of the plot
        - Use the _animated_artists list to add artists that will be animated and updated

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
        # width_inches = 15
        width_inches = 20
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
        
        # List to store artists that will be animated
        self._animated_artists = []
        
        # BlitManager will be initialized after plot_setup is called
        self._blit_manager = None

        # Add animated artists to the list
        self.plot_setup()

        # IMPORTANT: Make all animated artists invisible temporarily
        for artist in self._animated_artists:
            artist.set_visible(False)
        
        # Draw the canvas once to capture the background without animated artists
        self.canvas.draw()
        
        # Make artists visible again and set them as animated
        for artist in self._animated_artists:
            artist.set_visible(True)
            artist.set_animated(True)
        
        # Initialize the BlitManager
        self._blit_manager = self._BlitManager(self.canvas, self._animated_artists)

        # Force a redraw to show the animated artists
        self.canvas.draw()

    def get_plot(self):
        """
        Return the plot as a numpy array
        """
        # Convert to numpy array
        plot_array = np.array(self.canvas.renderer.buffer_rgba())
        
        # Convert RGBA to RGB
        plot_array = plot_array[:, :, :3]
        
        return plot_array
    
    def plot_setup(self):
        """ 
        Method for setting up the plot
        Child classes should override this method and add artists to _animated_artists
        list if they need to be animated
        """
        pass
    
    def update(self, custom_msg=None):
        """ 
        Method for updating the plot in animations 
        Child classes should override this method to update the artists
        and call self._blit_manager.update() after updating the artists
        """
        if self._blit_manager is not None:
            self._blit_manager.update()
            
    def add_animated_artist(self, artist):
        """
        Add an artist to be animated
        """
        if self._blit_manager is None:
            # If BlitManager hasn't been initialized yet, just add to our list
            self._animated_artists.append(artist)
        else:
            # If BlitManager is already initialized, add to both lists
            self._animated_artists.append(artist)
            self._blit_manager.add_artist(artist)
    
    class _BlitManager:
        """
        Integrated BlitManager to handle efficient canvas updates
        """
        def __init__(self, canvas, animated_artists=()):
            """
            Parameters
            ----------
            canvas : FigureCanvasAgg
                The canvas to work with, this only works for subclasses of the Agg
                canvas which have the `copy_from_bbox` and `restore_region` methods.

            animated_artists : Iterable[Artist]
                List of the artists to manage
            """
            self.canvas = canvas
            self._bg = None
            self._artists = []

            for a in animated_artists:
                self.add_artist(a)
                
            # grab the background on every draw
            self.cid = canvas.mpl_connect("draw_event", self.on_draw)
            
            # Capture the background immediately
            self._bg = canvas.copy_from_bbox(canvas.figure.bbox)

        def on_draw(self, event):
            """Callback to register with 'draw_event'."""
            cv = self.canvas
            if event is not None:
                if event.canvas != cv:
                    raise RuntimeError
            self._bg = cv.copy_from_bbox(cv.figure.bbox)
            self._draw_animated()

        def add_artist(self, art):
            """
            Add an artist to be managed.

            Parameters
            ----------
            art : Artist
                The artist to be added. Will be set to 'animated' (just
                to be safe). *art* must be in the figure associated with
                the canvas this class is managing.
            """
            if art.figure != self.canvas.figure:
                raise RuntimeError
            art.set_animated(True)
            self._artists.append(art)

        def _draw_animated(self):
            """Draw all of the animated artists."""
            fig = self.canvas.figure
            for a in self._artists:
                fig.draw_artist(a)

        def update(self):
            """Update the screen with animated artists."""
            cv = self.canvas
            fig = cv.figure
            # paranoia in case we missed the draw event,
            if self._bg is None:
                self.on_draw(None)
            else:
                # restore the background
                cv.restore_region(self._bg)
                # draw all of the animated artists
                self._draw_animated()
                # update the GUI state
                cv.blit(fig.bbox)
            # let the GUI event loop process anything it has to do
            try:
                cv.flush_events()
            except (AttributeError, NotImplementedError):
                # Some backend implementations may not support flush_events
                pass
