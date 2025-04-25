import matplotlib.pyplot as plt
import numpy as np
from collections import deque
from matplotlib.patches import Rectangle, Circle

from animation import AnimatorBase

class AnimatorSimple(AnimatorBase):
    def __init__(self):
        super().__init__()
        self.plot_setup()
    
    def plot_setup(self):
        # Example data points
        self.ax.scatter(
            [0, 0, 4.1, 4.1], 
            [3.3-1.6, -1.6, 3.3-1.6, -1.6], 
            # c='r', 
            color=(1, 0, 0),
            s=100)
        
        # plt.show()

    def update(self):
        pass

class Animator(AnimatorBase):
    """
    Example for creating an animation. Shows 
    - the robot position
    - the previous path of the robot
    - the thruster forces
    """
    def __init__(self):
        super().__init__()
        self.plot_setup()
    
    def plot_setup(self):
        self.ax.scatter(
            [0, 0, 4.1, 4.1], 
            [3.3-1.6, -1.6, 3.3-1.6, -1.6], 
            c='r', s=100)

        # Visualization parameters
        self.robot_width = 0.6
        self.robot_height = 0.6
        self.force_scaler = 0.5 # scale the force to a resonable size for visualization

        # Initialize state variables for initial plot
        self.position = np.zeros(2)
        self.orientation = 0.0
        self.angular_velocity = 0.0

        ## Robot position
        self.robot_rect = Rectangle(
            (0, 0), self.robot_width, self.robot_height,
            fill=False, linewidth=2, color='blue'
        )
        self.ax.add_patch(self.robot_rect)

        # Instead of arrow, use a line with marker for orientation
        self.orientation_arrow = self.ax.arrow(
            0, 0, 0, 0, head_width=0.1, head_length=0.2,
            fc='blue', ec='blue'
        )
        
        ## Robot path
        # Path storage
        self.path_duration = 30.0  # seconds
        self.update_rate = 0.1    # seconds
        self.path_points = int(self.path_duration / self.update_rate)
        self.robot_path = deque(maxlen=self.path_points)

        # Pre-fill path
        for _ in range(self.path_points):
            self.robot_path.append(np.zeros(2))

        self.robot_path_line, = self.ax.plot([], [], '-', color='blue', alpha=0.5)

        ## Thruster forces
        # Positions/orientations of thrusters
        val1 = 0.6 * self.robot_width/2
        val2 = self.robot_width/2
        self.pos_orient = np.array([
            [ val2, -val1,  1,  0],
            [-val2, -val1, -1,  0],
            [ val2,  val1,  1,  0],
            [-val2,  val1, -1,  0],
            [ val1,  val2,  0,  1],
            [ val1, -val2,  0, -1],
            [-val1,  val2,  0,  1],
            [-val1, -val2,  0, -1],
        ])

        # Create force arrows
        self.force_arrows = []
        for _ in range(8):
            self.force_arrows.append(
                self.ax.arrow(0, 0, 0, 0, head_width=0.05, head_length=0.1,
                            fc='black', ec='black', alpha=1.0)
            )

        self.forces = np.zeros(8)

    def update(self, msg):
        """
        Update the plot with new data.
        """
        # Split up into update_states and update_plot for clarity.
        self.update_states(msg)
        self.update_plot()

    def update_states(self, msg):
        """
        position: [2] array; x and y pos of the robot in m
        orientation: [1] float; orientation of the robot in rad
        angular_velocity: [1] float; angular velocity of the robot in rad/s
        forces: [8] array; forces of the thrusters in N
        """
        self.position = msg.position
        self.orientation = msg.orientation
        self.angular_velocity = msg.angular_velocity

    def update_plot(self):
        """
        Update all plot elements. Code involves mainly a lot of transformation from the
        local to global coordinate system, followed by a 'set_data' command.
        """
        # Calculate rotation matrix
        R = np.array([
            [np.cos(self.orientation), -np.sin(self.orientation)],
            [np.sin(self.orientation), np.cos(self.orientation)]
        ])
        
        ## Update robot position
        # Update rectangle position
        offset = R @ np.array([-self.robot_width/2, -self.robot_height/2])
        rect_x = self.position[0] + offset[0]
        rect_y = self.position[1] + offset[1]
        self.robot_rect.set_xy((rect_x, rect_y))
        self.robot_rect.angle = np.degrees(self.orientation)

        # Update orientation arrow
        arrow_length = max(self.robot_width, self.robot_height) * 0.6
        dx = arrow_length * np.cos(self.orientation)
        dy = arrow_length * np.sin(self.orientation)
        self.orientation_arrow.set_data(
            x=self.position[0], y=self.position[1],
            dx=dx, dy=dy
        )

        ## Update path
        robot_path_array = np.array(self.robot_path)
        self.robot_path_line.set_data(
            robot_path_array[:, 0], robot_path_array[:, 1]
        )

        ## Update thruster forces
        for i in range(8):
            if abs(self.forces[i]) < 1e-6:
                self.force_arrows[i].set_alpha(0.0)
                continue
            
            self.force_arrows[i].set_alpha(1.0)

            # local positions in robots own coordinate system
            start_point = np.array([self.pos_orient[i, 0], self.pos_orient[i, 1]])
            direction = np.array([self.pos_orient[i, 2], self.pos_orient[i, 3]])
            end_point = start_point + direction * self.forces[i] * self.force_scaler

            # clobal start and end points
            start_global = self.position + R @ start_point
            end_global = self.position + R @ end_point

            self.force_arrows[i].set_data(
                x=start_global[0], y=start_global[1],
                dx=end_global[0] - start_global[0],
                dy=end_global[1] - start_global[1]
            )

        ## Draw updated frame
        self.fig.canvas.draw()

if __name__ == "__main__":
    # ani = Animator()
    ani = AnimatorSimple()
    ani_img = ani.get_plot()
    plt.imshow(ani_img)
    plt.show()