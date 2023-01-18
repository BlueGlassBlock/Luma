import importlib
import importlib.metadata
import subprocess
import sys
from pathlib import Path

path_retriever = ["python", "-c", "import sys; [print(p) for p in sys.path]"]
res = subprocess.run(["pdm", "run"] + path_retriever, stdout=subprocess.PIPE)
sys_path = res.stdout.decode().splitlines()
sys.path.extend(sys_path)
importlib.import_module("graia.ariadne")
print(importlib.metadata.metadata("graia-broadcast"))
