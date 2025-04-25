import matplotlib.pyplot as plt
import numpy as np

from animation import AnimatorBase

class Animator(AnimatorBase):
    def __init__(self):
        super().__init__()
        self.plot_setup()
    
    def plot_setup(self):
        self.ax.grid(True)

        # Example data points
        self.ax.scatter(
            [0, 0, 4.1, 4.1], 
            [3.3-1.6, -1.6, 3.3-1.6, -1.6], 
            c='r', s=100)

    def update(self):
        pass

if __name__ == "__main__":
    ani = Animator()
    ani_img = ani.get_plot()
    plt.imshow(ani_img)
    plt.show()