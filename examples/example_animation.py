import matplotlib.pyplot as plt
import numpy as np
from collections import deque
from matplotlib.patches import Rectangle, Circle

from src.animation import AnimatorBase
# from aniTest import AnimatorBase

# Remove unused import
# from micro_orbiting_msgs.msg import ControllerValues

class AnimatorSimple(AnimatorBase):
    def __init__(self, dpi=100):
        super().__init__(dpi)
        # plot_setup is already called in AnimatorBase.__init__
        # Removing this redundant call: self.plot_setup()
    
    def plot_setup(self):
        # Example data points
        scatter = self.ax.scatter(
            [0, 0, 4.1, 4.1], 
            [3.3-1.6, -1.6, 3.3-1.6, -1.6], 
            color=(1, 0, 0),
            s=100)
        
        # Add a circle
        circle = Circle((0, 0), 0.5, color='blue', alpha=0.5)
        self.ax.add_patch(circle)

class Animator(AnimatorBase):
    """
    Example for creating an animation. Shows 
    - the robot position
    - the previous path of the robot
    - the thruster forces

    The animator uses blitting (see matplotlib doc) to increase the performance, although that is not
    strictly necessary.
    """
    def __init__(self, dpi=100):
        # Initialize base class first - this will call plot_setup
        super().__init__(dpi)
    
    def plot_setup(self):
        self.add_grid_and_ticks()

        # Visualization parameters
        self.robot_width = 0.6
        self.robot_height = 0.6
        self.force_scaler = 0.5 # scale the force to a reasonable size for visualization

        # Initialize state variables for initial plot
        self.position = np.zeros(2)
        self.orientation = 0.0
        self.angular_velocity = 0.0
        self.forces = np.zeros(8)

        ## Robot position
        self.robot_rect = Rectangle(
            (0, 0), self.robot_width, self.robot_height,
            fill=False, linewidth=2, color='blue'
        )
        self.ax.add_patch(self.robot_rect)
        self.add_animated_artist(self.robot_rect)

        ## Create orientation arrow
        # Use a Line2D instead of arrow for orientation
        arrow_length = max(self.robot_width, self.robot_height) * 0.6
        dx = arrow_length * np.cos(self.orientation)
        dy = arrow_length * np.sin(self.orientation)
        # self.orientation_line, = self.ax.plot(
        #     [self.position[0], self.position[0] + dx],
        #     [self.position[1], self.position[1] + dy],
        #     color='blue', lw=2
        # )
        self.orientation_line = self.ax.add_patch(
            plt.matplotlib.patches.FancyArrowPatch(
                (self.position[0], self.position[1]), 
                (self.position[0] + dx, self.position[1] + dy), 
                arrowstyle='->', mutation_scale=15, color='blue', lw=2
            )
        )
        self.add_animated_artist(self.orientation_line)
        
        ## Robot path
        # Path storage
        self.path_duration = 30.0  # seconds
        self.update_rate = 0.1    # seconds
        self.path_points = int(self.path_duration / self.update_rate)
        self.robot_path = deque(maxlen=self.path_points)

        # Pre-fill path
        for _ in range(self.path_points):
            self.robot_path.append(np.zeros(2))

        # Create path line
        robot_path_array = np.array(self.robot_path)
        self.robot_path_line, = self.ax.plot(
            robot_path_array[:, 0], 
            robot_path_array[:, 1], 
            '-', color='blue', alpha=0.5
        )
        self.add_animated_artist(self.robot_path_line)

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

        # Create force lines instead of arrows
        self.force_lines = []
        for i in range(8):
            # Local positions in robot's coordinate system
            start_point = np.array([self.pos_orient[i, 0], self.pos_orient[i, 1]])
            global_start = self.position + start_point
            
            # Add a simple line for now
            line, = self.ax.plot(
                [global_start[0], global_start[0]], 
                [global_start[1], global_start[1]], 
                color='black', alpha=0.0
            )
            self.force_lines.append(line)
            self.add_animated_artist(line)

    def update(self, msg):
        """
        Update the plot with new data.
        """
        # Split up into update_states and update_plot for clarity.
        self.update_states(msg)
        self.update_plot()
        # Call the base class update method 
        super().update()

    def update_states(self, msg):
        """
        position: [2] array; x and y pos of the robot in m
        orientation: [1] float; orientation of the robot in rad
        angular_velocity: [1] float; angular velocity of the robot in rad/s
        forces: [8] array; forces of the thrusters in N
        """
        self.position = [msg.x1, msg.y1]

        thres = 0.75
        if abs(self.robot_path[-1][0] - msg.x1) < thres and abs(self.robot_path[-1][1] - msg.y1) < thres:
            self.robot_path.append(np.array(self.position))
        else:
            # If the robot has moved more than thres meters in one step, probably some data is missing.
            self.robot_path = deque(np.array([self.position] *self.path_points) , maxlen=self.path_points)

        self.orientation = msg.alpha
        self.angular_velocity = msg.omega
        # TODO : Forces are currently ignored

    def update_plot(self):
        """
        Update all plot elements. Code involves mainly a lot of transformation from the
        local to global coordinate system, followed by updating the plot data.
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

        # Update orientation line
        arrow_length = max(self.robot_width, self.robot_height) * 0.6
        dx = arrow_length * np.cos(self.orientation)
        dy = arrow_length * np.sin(self.orientation)
        # self.orientation_line.set_data(
        #     [self.position[0], self.position[0] + dx],
        #     [self.position[1], self.position[1] + dy]
        # )
        self.orientation_line.set_positions(
            (self.position[0], self.position[1]), 
            (self.position[0] + dx, self.position[1] + dy)
        )

        ## Update path
        robot_path_array = np.array(self.robot_path)
        self.robot_path_line.set_data(
            robot_path_array[:, 0], robot_path_array[:, 1]
        )

        ## Update thruster forces
        for i in range(8):
            # Skip updating if force is too small
            if abs(self.forces[i]) < 1e-6:
                self.force_lines[i].set_alpha(0.0)
                continue
            
            self.force_lines[i].set_alpha(1.0)

            # Local positions in robot's own coordinate system
            start_point = np.array([self.pos_orient[i, 0], self.pos_orient[i, 1]])
            direction = np.array([self.pos_orient[i, 2], self.pos_orient[i, 3]])
            end_point = start_point + direction * self.forces[i] * self.force_scaler

            # Global start and end points
            start_global = self.position + R @ start_point
            end_global = self.position + R @ end_point

            # Update line data
            self.force_lines[i].set_data(
                [start_global[0], end_global[0]],
                [start_global[1], end_global[1]]
            )

    def add_grid_and_ticks(self):
        """
        Add a grid and ticks on the inside of the plot.
        """
        # Show the axes
        self.ax.grid(True, which='both', color='gray', linestyle='--', linewidth=0.75)
        self.ax.tick_params(axis='both', which='major', labelsize=18)

        # Adjust the tick labels to be inside the plot and not overlap with the grid
        self.ax.tick_params(axis="y", direction="in", pad=-35)
        for label in self.ax.yaxis.get_ticklabels():
            label.set_verticalalignment('bottom')

        self.ax.tick_params(axis="x", direction="in", pad=-15)
        for label in self.ax.xaxis.get_ticklabels():
            label.set_horizontalalignment('right') 

if __name__ == "__main__":
    ani = Animator()
    # ani = AnimatorSimple(dpi=100)
    ani_img = ani.get_plot()
    plt.imshow(ani_img)
    plt.show()
