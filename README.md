# Install 

This package depends on ffmpeg-python which needs to be installed from pip:

```bash
python3 -m <venvname> <myenvpath>
pip install ffmpeg-python
export PYTHONPATH=$PYTHONPATH:$(find <myenvpath>/<venvname> -name "site-packages" -type d | head -n 1)

cd <workspacepath>
colcon build
```

Best is to have `export PYTHONPATH=$PYTHONPATH:$(find <myenvpath>/<venvname> -name "site-packages" -type d | head -n 1)` in your `.bashrc`.
