import os
import shutil
import builtins
from CoverDownloader import does_companion_exist, original_print, primt
from colorama import Fore, Style, init
init()


global original_print

if not os.path.exists("married"):
    os.makedirs("married")

losers        = 0
couples_moved = 0
total_potential_couples = 0
original_print()
for file in os.listdir("."):
    if not (file.endswith(".mp3") or file.endswith(".flac")):
        continue
    filepath = os.path.join(".", file)
    if does_companion_exist(filepath):
        base_filename = os.path.splitext(file)[0]
        possible_filenames = [f"{base_filename}{suffix}" for suffix in ["", "A", "B"] + [f"B{i}" for i in range(1, 1000)]]
        possible_extensions = [".mp3", ".flac"] + [f"{ext}" for ext in [".jpg.jpg", ".jpg", ".jpeg", ".png", ".webp"]]
        possible_files = [f"{filename}{extension}" for filename in possible_filenames for extension in possible_extensions]
        for possible_file in possible_files:
            if os.path.isfile(os.path.join(".", possible_file)):
                new_root = os.path.join("married")
                os.makedirs(new_root, exist_ok=True)
                shutil.move(os.path.join(".", possible_file), os.path.join(new_root, possible_file))
        original_print(f"{Fore.GREEN}{Style.BRIGHT}{file} and its companions moved to married directory.")
        total_potential_couples += 1
        couples_moved += 1
    else:
        original_print(f"{Fore.RED}{Style.NORMAL}{file} unmarried & unmoved.")
        total_potential_couples += 1
        losers += 1

original_print(f"{Fore.CYAN}{Style.BRIGHT}\n* {couples_moved:4d} sets of married files were found (and moved).")
original_print(f"{Fore.BLUE}{Style.BRIGHT}* {losers:4d} losers couldn't get married because they had no partners. They will die alone.")
original_print(f"{Fore.GREEN}{Style.NORMAL}* {((couples_moved/total_potential_couples)*100):2.1f}% of {total_potential_couples} total potential couples were successfully married.")


