from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='space_lab_data_fusion',
            executable='online',
            name='online_data_fusion',
            parameters=[
                {"config_path": './src/space_lab_data_fusion/space_lab_data_fusion/config.yaml'},
                {"background_path": './src/space_lab_data_fusion/space_lab_data_fusion/test_data/background_IMG_3965.png'},
            ],
        ),
    ])