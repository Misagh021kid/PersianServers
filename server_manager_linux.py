from pathlib import Path
import os
import shutil
import subprocess
import json
import time
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent

SERVER_FILES_DIR = BASE_DIR / "server_files"
USER_SERVERS_DIR = BASE_DIR / "user_servers"
DATA_DIR = BASE_DIR / "data"
SERVER_DATA_FILE = DATA_DIR / "servers.json"

JAVA_PATH = "java"
START_PORT = 30000

os.makedirs(USER_SERVERS_DIR, exist_ok=True)
os.makedirs(SERVER_DATA_FILE.parent, exist_ok=True)

if not SERVER_DATA_FILE.exists():
    with open(SERVER_DATA_FILE, "w") as f:
        json.dump({}, f)

def load_data():
    with open(SERVER_DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(SERVER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_next_available_port(data):
    used_ports = {entry.get("port", START_PORT) for entry in data.values()}
    port = START_PORT
    while port in used_ports:
        port += 1
    return port

def screen_exists(screen_name):
    result = subprocess.run(["screen", "-ls"], capture_output=True, text=True)
    return screen_name in result.stdout

def create_server(user_id: str, version: str) -> str:
    data = load_data()
    user_path = USER_SERVERS_DIR / f"{user_id}_{version}"

    if user_path.exists():
        return "❗ Server ghablan sakhte shode."

    version_dir = SERVER_FILES_DIR / version
    template_jar = version_dir / "server.jar"
    cache_dir = version_dir / "cache"
    logo_file = version_dir / "server-icon.png"

    if not template_jar.exists():
        return f"❗ server.jar baraye version {version} mojood nist."
    if not cache_dir.exists():
        return f"❗ Cache folder baraye version {version} mojood nist."

   
    os.makedirs(user_path, exist_ok=True)

    shutil.copy(template_jar, user_path / "server.jar")


    shutil.copytree(cache_dir, user_path / "cache")

    if logo_file.exists():
        shutil.copy(logo_file, user_path / "server-icon.png")


    with open(user_path / "eula.txt", "w") as f:
        f.write("eula=true\n")

    port = get_next_available_port(data)
    with open(user_path / "server.properties", "w") as f:
        f.write(f"server-port={port}\n")

    data[user_id] = {
        "version": version,
        "status": "stopped",
        "pid": None,
        "port": port,
        "path": str(user_path),
        "start_time": None,
    }
    save_data(data)

    subprocess.run(["ufw", "allow", str(port)], check=True)
    return f"✅ Server ba movafaghiat sakhte shod roye port {port}."



def get_java_path(version: str) -> str:
    if version.startswith("1.16") or version.startswith("1.18"):
        return "/usr/lib/jvm/java-17-openjdk-amd64/bin/java"
    if version.startswith("1.20"):
        return "java"


def get_active_screens_count(prefix: str = "mc_") -> int:
    try:
        output = subprocess.check_output("screen -ls", shell=True).decode()
        lines = [line for line in output.splitlines() if prefix in line]
        return len(lines)
    except subprocess.CalledProcessError:
        return 0
    
def start_server(user_id: str) -> str:
    data = load_data()
    if user_id not in data:
        return "❗ Server peyda nashod."
    if get_active_screens_count() >= 6:
        return "❌ Be dalile mashghool bodan system, Felaan Nemitavanid Server Roshan Konid."

    if data[user_id]["status"] == "running" and screen_exists(f"mc_{user_id}"):
        return "✅ Server ghablan dar hale ejra ast."

    version = data[user_id]["version"]
    user_path = Path(data[user_id]["path"])
    java_path = get_java_path(version)
    jar_path = user_path / "server.jar"

    if not jar_path.exists():
        return f"❗ File server.jar mojood nist."
    
    screen_name = f"mc_{user_id}"
    command = f"screen -dmS {screen_name} {java_path} -Xms1536M -Xmx1536M -XX:+AlwaysPreTouch -XX:+DisableExplicitGC -XX:+ParallelRefProcEnabled -XX:+PerfDisableSharedMem -XX:+UnlockExperimentalVMOptions -XX:+UseG1GC -XX:G1HeapRegionSize=8M -XX:G1HeapWastePercent=5 -XX:G1MaxNewSizePercent=40 -XX:G1MixedGCCountTarget=4 -XX:G1MixedGCLiveThresholdPercent=90 -XX:G1NewSizePercent=30 -XX:G1RSetUpdatingPauseTimePercent=5 -XX:G1ReservePercent=20 -XX:InitiatingHeapOccupancyPercent=15 -XX:MaxGCPauseMillis=200 -XX:MaxTenuringThreshold=1 -XX:SurvivorRatio=32 -Dusing.aikars.flags=https://mcflags.emc.gs -Daikars.new.flags=true -jar server.jar nogui"
    subprocess.Popen(command, shell=True, cwd=user_path)

    data[user_id]["status"] = "running"
    data[user_id]["pid"] = None
    data[user_id]["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)

    return f"✅ Server shoro shod (Lotfan Ta Start Kamel Kami Montazer Bemanid)"

def stop_server(user_id: str) -> str:
    data = load_data()
    if user_id not in data:
        return "❗ Server peyda nashod."

    if data[user_id]["status"] != "running":
        return "❗ Server ejra nemishavad."

    screen_name = f"mc_{user_id}"
    if not screen_exists(screen_name):
        data[user_id]["status"] = "stopped"
        data[user_id]["pid"] = None
        save_data(data)
        return "⚠️ Server ejra nemishavad ya ghablan baste shode."

    subprocess.run(['screen', '-S', screen_name, '-p', '0', '-X', 'stuff', 'stop\n'])

    for _ in range(20): 
        time.sleep(1)
        if not screen_exists(screen_name):
            break

    if screen_exists(screen_name):
        subprocess.run(["screen", "-S", screen_name, "-X", "quit"])

    data[user_id]["status"] = "stopped"
    data[user_id]["pid"] = None
    data[user_id]["start_time"] = None
    save_data(data)
    return "🛑 Server ba movafaghiat stop shod."

def delete_server(user_id: str) -> str:
    data = load_data()
    if user_id not in data:
        return "❗ Server peyda nashod."

    port = data[user_id]["port"]
    if data[user_id]["status"] == "running":
        stop_server(user_id)

    user_path = Path(data[user_id]["path"])
    if user_path.exists():
        shutil.rmtree(user_path)

    del data[user_id]
    save_data(data)
    subprocess.run(["ufw", "deny", str(port)], check=True)
    return "🗑️ Server ba movafaghiat hazf shod."

def get_server_status(user_id: str) -> dict:
    data = load_data()
    if user_id not in data:
        return {"status": "not_found"}

    screen_name = f"mc_{user_id}"
    if data[user_id]["status"] == "running" and not screen_exists(screen_name):
        data[user_id]["status"] = "stopped"
        data[user_id]["pid"] = None
        save_data(data)

    return data[user_id]
def toggle_plugin(user_id: str, plugin_name: str) -> str:
    data = load_data()
    if user_id not in data:
        return "❗ Server peyda nashod."

    version = data[user_id]["version"]
    server_plugin_dir = Path(data[user_id]["path"]) / "plugins"
    source_plugin_path = SERVER_FILES_DIR / version / "plugins" / f"{plugin_name}.jar"
    dest_plugin_path = server_plugin_dir / f"{plugin_name}.jar"

    os.makedirs(server_plugin_dir, exist_ok=True)

    if dest_plugin_path.exists():
        os.remove(dest_plugin_path)
        return f"❌ Plugin `{plugin_name}` hazf shod."
    
    if not source_plugin_path.exists():
        return f"❗ Plugin `{plugin_name}` baraye version {version} mojood nist."

    shutil.copy(source_plugin_path, dest_plugin_path)
    return f"✅ Plugin `{plugin_name}` nasb shod."
from pathlib import Path

def toggle_property(user_id: str, key: str, default: bool = False) -> str:
    data = load_data()
    if user_id not in data:
        return f"❗ Server peyda nashod."

    server_path = Path(data[user_id]["path"])
    props_path = server_path / "server.properties"
    if not props_path.exists():
        return f"❗ File server.properties mojood nist."

    with open(props_path, "r") as f:
        lines = f.readlines()

    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            current = line.strip().split("=")[1].lower() == "true"
            new_value = not current
            lines[i] = f"{key}={'true' if new_value else 'false'}\n"
            found = True
            break

    if not found:
        new_value = not default
        lines.append(f"{key}={'true' if new_value else 'false'}\n")

    with open(props_path, "w") as f:
        f.writelines(lines)

    return f"🔄 {key.replace('-', ' ').title()} set Shod Roye: `{str(new_value).lower()}`."

def toggle_online_mode(user_id: str) -> str:
    return toggle_property(user_id, "online-mode", default=False)

def toggle_command_block(user_id: str) -> str:
    return toggle_property(user_id, "enable-command-block", default=False)

def toggle_pvp(user_id: str) -> str:
    return toggle_property(user_id, "pvp", default=True)

def toggle_hardcore(user_id: str) -> str:
    return toggle_property(user_id, "hardcore", default=False)

def toggle_white_list(user_id: str) -> str:
    return toggle_property(user_id, "white-list", default=False)

def toggle_monster(user_id: str) -> str:
    return toggle_property(user_id, "spawn-monsters", default=True)
def get_current_view_distance(user_id: str) -> str:
    data = load_data()
    if user_id not in data:
        return "?"

    server_path = Path(data[user_id]["path"])
    props_path = server_path / "server.properties"
    if not props_path.exists():
        return "?"

    with open(props_path, "r") as f:
        for line in f:
            if line.startswith("view-distance="):
                return line.strip().split("=")[1]
    return "?"

def set_motd(user_id: str, motd: str) -> str:
    data = load_data()
    if user_id not in data:
        return "❗ Server peyda nashod."

    server_path = Path(data[user_id]["path"])
    props_path = server_path / "server.properties"
    if not props_path.exists():
        return "❗ File server.properties mojood nist."

    updated = False
    with open(props_path, "r") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if line.startswith("motd="):
            lines[i] = f"motd={motd}\n"
            updated = True
            break

    if not updated:
        lines.append(f"motd={motd}\n")

    with open(props_path, "w") as f:
        f.writelines(lines)

    return f"📢 MOTD set shod be: `{motd}`."
def set_view_distance(user_id: str, distance: int) -> str:
    data = load_data()
    if user_id not in data:
        return "❗ Server peyda nashod."

    server_path = Path(data[user_id]["path"])
    props_path = server_path / "server.properties"
    if not props_path.exists():
        return "❗ File server.properties mojood nist."

    updated = False
    with open(props_path, "r") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if line.startswith("view-distance="):
            lines[i] = f"view-distance={distance}\n"
            updated = True
            break

    if not updated:
        lines.append(f"view-distance={distance}\n")

    with open(props_path, "w") as f:
        f.writelines(lines)

    return f"📏 View Distance set shod be `{distance}`."

def is_server_running(user_id: str) -> bool:
    """Check if the server screen session is running."""
    result = subprocess.run(["screen", "-ls"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return f"mc_{user_id}" in result.stdout

def toggle_whitelist_player(user_id: str, player: str) -> str:
    if not is_server_running(user_id):
        return "❗ Server roshan nist. Lotfan server ro roshan konid."

    whitelisted_players = get_whitelisted_players(user_id)

    if player.lower() in [p.lower() for p in whitelisted_players]:
        run_console_command(user_id, f"whitelist remove {player}")
        return f"❌ Player {player} az whitelist hazf shod"
    else:
        run_console_command(user_id, f"whitelist add {player}")
        return f"✅ Player {player} be whitelist ezafe shod"

def run_console_command(user_id: str, command: str):
    os.system(f"screen -S mc_{user_id} -X stuff '{command}\n'")

def get_whitelisted_players(user_id: str) -> list[str]:
    server_path = Path(load_data()[user_id]["path"])
    whitelist_path = server_path / "whitelist.json"
    if not whitelist_path.exists():
        return []
    
    import json
    with open(whitelist_path, "r") as f:
        try:
            data = json.load(f)
            return [entry["name"] for entry in data]
        except:
            return []

def restart_server(user_id: str) -> str:
    stop_msg = stop_server(user_id)
    if "❗" in stop_msg or "sagami" in stop_msg:
        return f"⛔ Restart failed: {stop_msg}"

    time.sleep(3)

    start_msg = start_server(user_id)
    return f"🔁 Restart complete:\n{start_msg}"