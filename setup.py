from setuptools import find_packages, setup

package_name = 'space_lab_data_fusion'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=[
        'setuptools',
        'ffmpeg-python',
        ],
    zip_safe=True,
    maintainer='sml-laptop-1',
    maintainer_email='raphaelsemail@posteo.eu',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'online = space_lab_data_fusion.online:main',
        ],
    },
)
