"""
There are 3 actions with files:
- just copy files from FPGA-folder to destination BUILD-folder
- just copy files from OS_DEV-folder to destination BUILD-folder
- change some data in files from FPGA-folder
"""
import os
import sys

# parse input args for this flag
global_ignore_err = False
# current path
global_cur_path = ""
# current fifo name
global_cur_fifo = ""
# buffer to save info about deleted device
global_device_buf = ""
# dtb file name
global_dtb_file_name = "radiomodule.dtb"


# make pretty output
class TtyColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def exist(file_name) -> None:
    """
    Check if file exist in current directory
    :param file_name:  file name to search for
    :return:  None
    """
    if not os.path.isfile(file_name):
        print("\t{}File {}\"{}\"{} doesn't exist{}".format(TtyColors.FAIL, TtyColors.WARNING, file_name,
                                                           TtyColors.FAIL, TtyColors.ENDC))
        # when ignore errors flag is not set than terminate the program
        if not global_ignore_err:
            exit(1)
    else:
        print("\t{}File {}\"{}\"{} exist{}".format(TtyColors.OKGREEN, TtyColors.WARNING, file_name, TtyColors.OKGREEN,
                                                   TtyColors.ENDC))
        # delete -x mode form file
        os.chmod(file_name, 0o666)


def create_full_path(file_name) -> str:
    """
    Add current directory path to the file name
    :param file_name:  the name of the file to append to
    :return:  file name with path
    """
    return global_cur_path + "/" + file_name


def search_similar(search, line) -> bool:
    """
    Search entry in line
    :param search:  base to search for
    :param line:  where to search
    :return:  True if found, False otherwise
    """
    if line.find(search) == -1:
        return False  # didn't find
    else:
        return True


def get_fifo_name(line) -> str:
    """
    Get fifo name from line
    :param line:  line where to search for
    :return:  Fifo name on success, empty string otherwise
    """
    try:
        fifo = line.split(" ")
        return fifo[1]
    except Exception:
        print("{}Can't get fifo name from line{}".format(TtyColors.FAIL, TtyColors.ENDC))
        return ""


def fifo_add_header(new_file) -> None:
    header = "/*------------------------------------------*\n" \
                 " *   PARAMS BELOW ARE ADDED AUTOMATICALLY   *\n" \
                 " *------------------------------------------*/\n" \
                 "/*+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++*/\n"
    new_file.write(header)


def fifo_add_end(new_file) -> None:
    end = "/*+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++*/\n"
    new_file.write(end)


def fifo_add(new_file) -> None:
    """
    Save new data to new file
    :return:  None
    """
    add_fifo = \
        [
            "\t\t\txlnx,tx-max-pkt-size = <511>;\n",
            "\t\t\txlnx,rx-min-pkt-size = <1>;\n",
        ]

    # add header to file
    fifo_add_header(new_file)

    print("\n{}Added to fifo {}{}{}\n".format(TtyColors.OKCYAN, TtyColors.WARNING, global_cur_fifo, TtyColors.ENDC))
    for line in add_fifo:
        new_file.write(line)
        print("{}+\t{}{}".format(TtyColors.OKGREEN, line.strip("\n\t"), TtyColors.ENDC))

    # add end to file
    fifo_add_end(new_file)


def device_delete_info() -> None:
    """
    Print info about deleted device
    :return:  None
    """
    print("\n{}Deleted next device {}{}\n".format(TtyColors.OKCYAN, TtyColors.WARNING, TtyColors.ENDC))
    print("{}{}{}".format(TtyColors.FAIL, global_device_buf, TtyColors.ENDC), end="")


def comment_device(new_file, start: bool) -> None:
    """
    Comment device in dtsi file
    :param new_file:  where to write
    :param start:  When True write before device, after device otherwise
    :return:  None
    """
    del_header = "/*-----------------------------------------*\n" \
                 " * DEVICE BELOW IS COMMENTED AUTOMATICALLY *\n" \
                 " *-----------------------------------------*/\n"
    del_body = "/*\n"
    del_end = "*/\n"

    if start:
        new_file.write(del_header)
        new_file.write(del_body)
    else:
        new_file.write(del_end)
        # print info about deleted device
        device_delete_info()


def parse_devices(line, new_file, act) -> bool:
    """
    Find devices from list devices
    :param line:  where to find
    :param new_file:  where to write
    :param act:  When True end device commenting, try to find device otherwise
    :return:  True when device was found, False otherwise
    """
    # devices to find
    devices = \
        [
            "sdra_axi_ad9361_a",
            "sdrb_axi_ad9361_b"
        ]

    end_device_description = r"};"

    global global_device_buf
    # when device was already found on previous iteration
    if act:
        if search_similar(end_device_description, line):
            new_file.write(line)
            # add device info to buffer
            global_device_buf = global_device_buf + "-" + "\t" + line.strip("\t")
            comment_device(new_file, False)
            global_device_buf = ""  # clear buffer
            return True
        # add device info to buffer
        global_device_buf = global_device_buf + "-" + "\t" + "\t" + line.strip("\t")

    # search for needed devices
    for dev in devices:
        if search_similar(dev, line):
            comment_device(new_file, True)
            # add device info to buffer
            global_device_buf = global_device_buf + "-" + "\t" + line.strip("\t")
            return True

    return False


def parse_fifo(line, new_file, act) -> bool:
    """
    Parse file-array (pl.dtsi) to find fifo in device-tree
    :param line:  where to find
    :param new_file:  where to write
    :param act:  When True end adding to fifo, try to find fifo otherwise
    :return:  True when fifo was found, False otherwise
    """
    fifo_base = r"axi_fifo_mm_s@"
    past_after = r"xlnx,use-tx-data = <0x1>;"

    if act:
        if search_similar(past_after, line):
            new_file.write(line)
            fifo_add(new_file)
            return True

    global global_cur_fifo
    if search_similar(fifo_base, line):
        global_cur_fifo = get_fifo_name(line)
        return True

    return False


def rename_pl_dtsi(name) -> str:
    """
    Rename pl.dtsi to mod_pl.dtsi
    :param name:  pl.dtsi
    :return:  New string on success, empty string otherwise
    """
    try:
        pos = name.split('/')
        pos[-1] = "mod_" + pos[-1]
    except Exception:
        print("\n{}Can't rename {}{}".format(TtyColors.FAIL, name, TtyColors.ENDC))
        exit(1)
    else:
        return "/".join(pos)


def print_total_info(new_file_name, fifo, devices) -> None:
    """
    Print summary information about deleted devices and added data to fifo
    :param new_file_name:
    :param fifo:
    :param devices:
    :return:
    """
    # print info about fifo
    if not fifo:
        print("\n{}Didn't find any fifo in file {}{}".format(TtyColors.FAIL, new_file_name, TtyColors.ENDC))
    else:
        print("\n{}Added data to {} fifo{}".format(TtyColors.WARNING, fifo, TtyColors.ENDC))

    # print info about devices
    if not devices:
        print("{}Didn't find needed devices in file {}{}\n".format(TtyColors.FAIL, new_file_name, TtyColors.ENDC))
    else:
        print("{}Deleted {} device(s){}\n".format(TtyColors.WARNING, devices, TtyColors.ENDC))


def parse_file(lines, new_file, new_file_name) -> None:
    """
    Parse file where delete devices and add data to fifo
    :param lines:  file data
    :param new_file:  where to save new modified data
    :param new_file_name:  new file name where to save data
    :return:  None
    """
    device_act = False
    fifo_act = False
    total_fifo = 0
    total_devices = 0

    for line in lines:
        # search for devices-base
        ret = parse_devices(line, new_file, device_act)
        # when device was commented need to avoid writing "};" to new file
        if ret and device_act:
            device_act = False
            continue
        # device was found
        if ret:
            total_devices += 1
            device_act = True

        # search for fifo base
        ret = parse_fifo(line, new_file, fifo_act)
        # when to fifo was added new data
        if ret and fifo_act:
            fifo_act = False
            continue
        # fifo was found
        if ret:
            total_fifo += 1
            fifo_act = True

        # write line to new file
        new_file.write(line)

    new_file.close()
    # change mode for file (make it green)
    os.chmod(new_file_name, 0o777)
    # print total info about fifo and devices
    print_total_info(new_file_name, total_fifo, total_devices)


def parse_pl_dtsi(work_file) -> None:
    """
    Parse pl.dtsi
    :param work_file:  name of the file
    :return:  None
    """
    # check again if pl.fifo and terminate even with error ignoring
    if not os.path.isfile(work_file):
        print("\n{}Can't find file name \"{}\"{}".format(TtyColors.FAIL, work_file, TtyColors.ENDC))
        exit(1)

    # open pl.dtsi file for parsing
    with open(work_file) as f:
        # read file to tmp array
        lines = f.readlines()
        # create name for new file
        mod_fifo = rename_pl_dtsi(work_file)
        # open new_file where to write modified pl.dtsi
        try:
            mod_pl = open(mod_fifo, "w")
        except IOError:
            print("\n{}Can't open file \"{}\"{}".format(TtyColors.FAIL, mod_fifo, TtyColors.ENDC))
            exit(1)

        # start parsing file
        parse_file(lines, mod_pl, work_file)


def process_fpga_files() -> None:
    """
    Process FPGA files: check if files exist; add new data
    :return:  None
    """
    files = \
        [
            r"pcw.dtsi",
            r"pl.dtsi",
            r"zynq-7000.dtsi"
        ]

    # create full path to file
    for c in range(len(files)):
        files[c] = create_full_path(files[c])

    # check for files in current directory
    print("\n{}Сheck for FPGA-files in current directory:{}\n".format(TtyColors.OKCYAN, TtyColors.ENDC))
    for f in files:
        exist(f)

    # parse pl.dtsi and create new file with modified data
    work_file = files[1]
    parse_pl_dtsi(work_file)
    # change pl.dtsi mode again (after reading mode can be changed by OS)
    os.chmod(work_file, 0o666)


def process_os_dev_files() -> None:
    """
    This function checks OS-dev files in current directory
    :return: None
    """
    # these files should be given by the OS-developers
    files = \
        [
            r"adi-fmcomms2.dtsi",
            r"ethernet.dtsi",
            r"pl_ad9361.dtsi",
            r"pl_int_rs485.dtsi",
            r"pl_software.dtsi",
            r"qspi.dtsi",
            r"system-top.dts"
        ]

    # create full path to file
    for c in range(len(files)):
        files[c] = create_full_path(files[c])

    # check for files in current directory
    print("\n{}Check for OS-developers files in current directory:{}\n".format(TtyColors.OKCYAN, TtyColors.ENDC))
    for f in files:
        exist(f)


# this flag will ignore all errors when specified
if "-i" in sys.argv:
    global_ignore_err = True

# set current path
global_cur_path = os.getcwd()

# process os-developers files
process_os_dev_files()

# process fpga files
process_fpga_files()

# create dtb
try:
    os.system("dtc -I dts system-top.dts -O dtb -o {}".format(global_dtb_file_name))
except Exception:
    print("\n{}Can't create DTB file {}{}\n".format(TtyColors.FAIL, global_dtb_file_name, TtyColors.ENDC))
else:
    print("\n{}DTB file {}\"{}\"{} created successfully{}\n".format(TtyColors.OKGREEN, TtyColors.WARNING,
                                                                    global_dtb_file_name, TtyColors.OKGREEN,
                                                                    TtyColors.ENDC))
    # make it green (execution mode)
    os.chmod(global_dtb_file_name, 0o777)
