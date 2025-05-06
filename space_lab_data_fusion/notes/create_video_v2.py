#!/usr/bin/env python3
import rclpy
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message
import rosbag2_py
from micro_orbiting_msgs.msg import ControllerValues, FailedActuators

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from collections import deque
import cv2
from pathlib import Path
import tempfile
from dataclasses import dataclass
from typing import Optional
import math

@dataclass
class TimedState:
    timestamp: int  # nanoseconds
    controller_values: Optional[ControllerValues] = None
    failed_actuators: Optional[FailedActuators] = None

class OfflineVisualizer:
    def __init__(self):
        # Visualization parameters (same as RealTimeVisualizer)
        self.robot_width = 0.6
        self.robot_height = 0.6
        self.force_scaler = 0.15
        self.plot_limits = [0, 4.10, -1.60, 1.70]  # [xmin, xmax, ymin, ymax]
        self.max_force = 1.75
        
        # Initialize state variables
        self.position = np.zeros(2)
        self.orientation = 0.0
        self.angular_velocity = 0.0
        self.center_position = np.zeros(2)
        self.center_pos_full = np.zeros(5)
        self.resulting_force = np.zeros(3)
        self.desired_state = np.zeros(6)
        
        # Path storage
        self.path_duration = 30.0  # seconds
        self.update_rate = 0.1    # seconds
        self.path_points = int(self.path_duration / self.update_rate)
        self.robot_path = deque(maxlen=self.path_points)
        self.center_path = deque(maxlen=self.path_points)
        
        # Pre-fill paths
        for _ in range(self.path_points):
            self.robot_path.append(np.zeros(2))
            self.center_path.append(np.zeros(2))

        # Set up the plot
        self.fig, self.ax = plt.subplots(figsize=(10, 10))
        self.ax.set_xlim(self.plot_limits[0], self.plot_limits[1])
        self.ax.set_ylim(self.plot_limits[2], self.plot_limits[3])
        self.ax.set_aspect('equal')
        # self.ax.grid(True)

        # Create visualization elements (same as RealTimeVisualizer)
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

        self.center_point = Circle(
            (0, 0), radius=0.075, color='red',
            alpha=0.5, fill=True
        )
        self.ax.add_patch(self.center_point)

        self.desired_point = Circle(
            (0, 0), radius=0.03, color='black', fill=True
        )
        self.ax.add_patch(self.desired_point)

        self.connection_line, = self.ax.plot([], [], '--', color='gray')
        self.robot_path_line, = self.ax.plot([], [], '-', color='blue', alpha=0.5)
        self.center_path_line, = self.ax.plot([], [], '-', color='red', alpha=0.5)

        # Force visualization setup
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
        self.failed_force_arrows = []
        for _ in range(8):
            self.force_arrows.append(
                self.ax.arrow(0, 0, 0, 0, head_width=0.05, head_length=0.1,
                            fc='black', ec='black', alpha=1.0)
            )
            self.failed_force_arrows.append(
                self.ax.arrow(0, 0, 0, 0, head_width=0.05, head_length=0.1,
                            fc='red', ec='red', alpha=1.0)
            )

        self.forces = np.zeros(8)
        self.failed_actuator_forces = np.zeros(8)

    def update_controller_values(self, msg):
        """Update state from ControllerValues message"""
        self.position = np.array([msg.x1, msg.y1])
        self.orientation = msg.alpha
        self.angular_velocity = msg.omega
        self.center_position = np.array([msg.center_state_x, msg.center_state_y])
        self.center_pos_full = np.array([
            msg.center_state_x, msg.center_state_y,
            msg.center_state_vx, msg.center_state_vy,
            msg.center_state_omega
        ])
        self.forces = np.array(msg.u_full)
        # Account for numerical inaccuracies
        for i in range(8):
            if abs(self.forces[i]) < 1e-5:
                self.forces[i] = 0.0

        self.resulting_force = np.array(msg.u)

        if len(msg.desired_state) > 0:
            self.desired_state = np.array(msg.desired_state)
            self.last_desired_state = self.desired_state
        else:
            self.desired_state = self.last_desired_state
        
        # Update paths
        self.robot_path.append(self.position)
        self.center_path.append(self.center_position)

    def update_failed_actuators(self, msg):
        """Update failed actuators from FailedActuators message"""
        self.failed_actuator_forces = np.zeros(8)
        for failure in msg.failed_actuators:
            idx = failure.idx
            self.failed_actuator_forces[idx] = failure.intensity * self.max_force

    def update_plot(self):
        """Update all plot elements"""
        # Calculate rotation matrix
        R = np.array([
            [np.cos(self.orientation), -np.sin(self.orientation)],
            [np.sin(self.orientation), np.cos(self.orientation)]
        ])
        
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

        # Update points and connection
        self.center_point.center = self.center_position
        self.desired_point.center = self.desired_state[:2]
        self.connection_line.set_data(
            [self.position[0], self.center_position[0]],
            [self.position[1], self.center_position[1]]
        )

        # Update force arrows
        self._update_forces(self.forces, self.force_arrows, R)
        self._update_forces(self.failed_actuator_forces, self.failed_force_arrows, R)

        # Update paths
        robot_path_array = np.array(self.robot_path)
        center_path_array = np.array(self.center_path)
        self.robot_path_line.set_data(
            robot_path_array[:, 0], robot_path_array[:, 1]
        )
        self.center_path_line.set_data(
            center_path_array[:, 0], center_path_array[:, 1]
        )

        # Draw and get frame
        self.fig.canvas.draw()
        return np.frombuffer(self.fig.canvas.tostring_rgb(), dtype=np.uint8).reshape(
            self.fig.canvas.get_width_height()[::-1] + (3,)
        )

    def _update_forces(self, forces, force_arrows, R):
        """Update force arrow positions and visibility"""
        for i in range(8):
            if abs(forces[i]) < 1e-6:
                force_arrows[i].set_alpha(0.0)
                continue
            
            force_arrows[i].set_alpha(1.0)
            start_point = np.array([self.pos_orient[i, 0], self.pos_orient[i, 1]])
            direction = np.array([self.pos_orient[i, 2], self.pos_orient[i, 3]])
            end_point = start_point + direction * forces[i] * self.force_scaler

            start_global = self.position + R @ start_point
            end_global = self.position + R @ end_point

            force_arrows[i].set_data(
                x=start_global[0], y=start_global[1],
                dx=end_global[0] - start_global[0],
                dy=end_global[1] - start_global[1]
            )

def process_bag(bag_path, output_path, fps=30):
    """Process a ROS2 bag and create a video with real-time timing"""
    # Initialize storage reader
    storage_options = rosbag2_py.StorageOptions(
        uri=str(bag_path),
        storage_id='sqlite3'
    )
    converter_options = rosbag2_py.ConverterOptions('', '')
    reader = rosbag2_py.SequentialReader()
    reader.open(storage_options, converter_options)

    # Get topic types
    topic_types = reader.get_all_topics_and_types()
    type_map = {topic.name: topic.type for topic in topic_types}

    # Initialize visualizer
    visualizer = OfflineVisualizer()
    
    # Initialize video writer setup
    temp_dir = Path(tempfile.mkdtemp())
    frame_dir = temp_dir / "frames"
    frame_dir.mkdir()

    # Collect all messages with their timestamps
    states = []
    start_time = None
    
    while reader.has_next():
        topic_name, data, t = reader.read_next()
        msg_type = get_message(type_map[topic_name])
        msg = deserialize_message(data, msg_type)
        
        if start_time is None:
            start_time = t
        
        if topic_name == '/px4_mpc/controller_values':
            state = TimedState(timestamp=t, controller_values=msg)
            states.append(state)
        elif topic_name == '/micro_orbiting/failed_actuators':
            # Find the closest controller values state and add failed actuators
            if states:
                closest_state = min(states, key=lambda x: abs(x.timestamp - t))
                closest_state.failed_actuators = msg

    # Process states into frames based on timing
    frame_time_ns = int(1e9 / fps)  # nanoseconds per frame
    current_time = start_time
    frame_count = 0
    
    last_state_idx = 0
    end_time = states[-1].timestamp if states else start_time
    
    while current_time <= end_time:
        # Find the state closest to the current time
        while (last_state_idx < len(states) - 1 and 
               states[last_state_idx + 1].timestamp <= current_time):
            last_state_idx += 1
        
        state = states[last_state_idx]
        
        # Update visualizer with state
        if state.controller_values:
            visualizer.update_controller_values(state.controller_values)
        if state.failed_actuators:
            visualizer.update_failed_actuators(state.failed_actuators)
            
        # Create and save frame
        frame = visualizer.update_plot()
        frame_path = frame_dir / f"frame_{frame_count:06d}.png"
        cv2.imwrite(str(frame_path), cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        frame_count += 1
        
        # Increment time by frame duration
        current_time += frame_time_ns

    # Create video from frames
    if frame_count > 0:
        frame = cv2.imread(str(frame_dir / "frame_000000.png"))
        height, width = frame.shape[:2]
        
        video_writer = cv2.VideoWriter(
            str(output_path),
            cv2.VideoWriter_fourcc(*'mp4v'),
            fps,
            (width, height)
        )

        for i in range(frame_count):
            frame_path = frame_dir / f"frame_{i:06d}.png"
            frame = cv2.imread(str(frame_path))
            video_writer.write(frame)

        video_writer.release()

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Convert ROS2 bag to real-time video')
    parser.add_argument('bag_path', type=Path, help='Path to ROS2 bag')
    parser.add_argument('output_path', type=Path, help='Path for output video')
    parser.add_argument('--fps', type=int, default=30, help='Output video FPS')
    args = parser.parse_args()

    process_bag(args.bag_path, args.output_path, args.fps)

if __name__ == '__main__':
    main()