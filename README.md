# Install 

This package depends on ffmpeg-python which needs to be installed from pip:

```bash
python3 -m <venvname> <myenvpath>
pip install ffmpeg-python
export PYTHONPATH=$PYTHONPATH:$(find <myenvpath>/<venvname> -name "site-packages" -type d | head -n 1)

cd <workspacepath>
colcon build
```

```
rosdep install --from-paths src -y --ignore-src
export PYTHONPATH=$PYTHONPATH:$(find ~/python_venvs/labdata_streamer/ -name "site-packages" -type d | head -n 1)
```

Best is to have `export PYTHONPATH=$PYTHONPATH:$(find <myenvpath>/<venvname> -name "site-packages" -type d | head -n 1)` in your `.bashrc`.

# Run

```bash
ros2 run space_lab_data_fusion online --ros-args --param background_path:='./src/space_lab_data_fusion/space_lab_data_fusion/test_data/background_IMG_3965.png'
```
