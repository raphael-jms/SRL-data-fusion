# Install 

This package depends on ffmpeg-python which requires a custom rosdep rule:

```bash
# Add the custom rosdep rule
sudo cp ./src/space_lab_data_fusion/rosdep/ffmpeg_python.yaml /etc/ros/rosdep/sources.list.d/
rosdep update

# Install dependencies
rosdep install --from-paths src --ignore-src -r -y
```