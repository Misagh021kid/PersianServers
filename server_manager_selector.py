import platform

system = platform.system()
# Windows didnt Support at this moment
if system == "Windows":
    from server_manager_linux import *
else:
    from server_manager_linux import *

