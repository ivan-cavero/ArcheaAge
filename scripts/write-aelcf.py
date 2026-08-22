import json, os, sys

launcher_dir = os.path.expandvars(r"%LOCALAPPDATA%\ArcheaAge\instances\1.2\Launcher\AAEmu.Launcher")
game_exe = os.path.expandvars(r"%LOCALAPPDATA%\ArcheaAge\instances\1.2\bin32\archeage.exe")
path = os.path.join(launcher_dir, "settings.aelcf")

cfg = json.load(open(path))
cfg["pathToGame"] = game_exe
cfg["serverIPAddress"] = "127.0.0.1"
cfg["loginType"] = "trino_1_2"
cfg["lastLoginUser"] = "test"
cfg["lastLoginPass"] = "test"
cfg["saveLoginAndPassword"] = True
json.dump(cfg, open(path, "w"), indent=2)

print("pathToGame  :", cfg["pathToGame"])
print("serverIP    :", cfg["serverIPAddress"])
print("loginType   :", cfg["loginType"])
print("user/pass   :", cfg["lastLoginUser"], "/", cfg["lastLoginPass"])