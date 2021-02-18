from pathlib import Path
from time import sleep
from sys import exit
import subprocess
import json
import os


def get_valid_input(prompt, is_valid):
    while True:
        result = input(prompt)
        if is_valid(result):
            return result


def yes_or_no(prompt):
    x = get_valid_input(prompt, lambda x: x in ["y", "Y", "n", "N"])
    return x in ["y", "Y"]


def is_this_ok():
    if not yes_or_no("Is this ok? (y/n): "):
        exit(0)


def is_valid_int(s):
    try:
        int(s)
        return True
    except:
        return False


def system_dialog():
    systems = [x.name for x in Path("/usr/bin").iterdir()
               if x.name.startswith("qemu-system-")]
    if Path("/usr/bin/qemu-kvm").exists():
        systems = ["qemu-kvm"] + systems

    print("Choose a system for running QEMU.")
    print("\n".join(f"{i+1}: {s}" for i, s in enumerate(systems)))
    choice = get_valid_input(
        "choice: ",
        lambda x: x in [str(y) for y in range(1, len(systems) + 1)]
    )
    choice = systems[int(choice) - 1]
    return (
        choice,
        [],     # variables
        choice  # arguments
    )


def video_dialog():
    print("""Please select a video adapter.
    1. STD - always works, bad performance
    2. QXL - usually works, better performance.
    3. virtio - only works on Linux>=4.4 with mesa, best performance
    4. nographic - still emulates a display, but doesn't show it
    5. none - can't even be accessed from VNC""")
    choice = get_valid_input("choice: ",
                             lambda x: x in [str(y) for y in range(1, 6)])
    choice = ["std", "qxl", "virtio", "nographic", "NONE"][int(choice) - 1]
    return (
        choice,
        ["VIDEO=" + choice],  # variables
        "-vga $VIDEO"         # arguments
    )


def memory_dialog():
    memory = int(get_valid_input(
        "RAM (in megabytes): ",
        lambda x: is_valid_int(x) and int(x) > 0
    ))
    return (
        memory,
        [f"MEMORY={memory}M"],  # variables
        "-m $MEMORY"            # arguments
    )


def cores_dialog():
    from multiprocessing import cpu_count
    core_count = int(get_valid_input(
        "core count (you have " + str(cpu_count()) + "): ",
        lambda x: x in [str(y) for y in range(1, cpu_count() + 1)]
    ))
    return (
        core_count,
        [f"CPU_CORES={core_count}"],  # variables
        "-smp $CPU_CORES"             # arguments
    )


# TODO: ask for SPICE and port forwarding
print("QEMU wizard\n")
size = input("image.qcow2 max size (default 20G, dynamically resized): ")
if size == "":
    size = "20G"

system = system_dialog()
memory = memory_dialog()
cores = cores_dialog()
video = video_dialog()

print("\nSUMMARY:\n")
print("system:", system[0])
print("memory:", memory[0])
print(" cores:", cores[0])
print(" video:", video[0])
print("  size:", size)
print()

is_this_ok()

print("Creating image...", end="")
allocation_proc = subprocess.run([
    "qemu-img", "create", "-f", "qcow2", "image.qcow2", size
], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
if allocation_proc.returncode != 0:
    print("\nError creating image:", allocation_proc.stdout)
    exit(1)
print(" Done!")

dialog_results = [system, memory, video, cores]

variables = sum((x[1] for x in dialog_results), start=[])
command = " ".join(x[2] for x in dialog_results)
command += " -drive file=image.qcow2,format=qcow2"

script = "\n".join(variables) + "\n\n" + command

if yes_or_no("Would you like to install an operating system now? (y/n): "):
    install_iso = Path("install.iso")

    while not install_iso.exists():
        print("Please rename your ISO to install.iso")
        sleep(1)

    cmd = "; ".join(variables) + "; " + command + " -cdrom install.iso"
    cmd = "bash -c " + json.dumps(cmd).replace("$", "\\$")
    print(cmd)
    os.system(cmd)

print("Done! Saving run.sh.")
with open("run.sh", "w") as f:
    f.write(script)

# -drive file=image.qcow2,format=qcow2
# -cdrom boot.iso
# -nic user
