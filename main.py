from group import Group
from bot import Bot
import sys
import os


def lowpriority():
    """ Set the priority of the process to below-normal."""
    try:
        sys.getwindowsversion()
    except AttributeError:
        isWindows = False
    else:
        isWindows = True

    if isWindows:
        import win32api,win32process,win32con

        pid = win32api.GetCurrentProcessId()
        handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
        win32process.SetPriorityClass(handle, win32process.BELOW_NORMAL_PRIORITY_CLASS)
    else:
        os.nice(19)


def main():
    if len(sys.argv) != 2:
        print("Error. Write data directory")
        return
    lowpriority()
    os.chdir(sys.argv[1])
    bot = Bot()
    app = Group(bot)
    app.run()


if __name__ == "__main__":
    main()
