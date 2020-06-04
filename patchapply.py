import filecmp as fc
import logging
import os
import tkinter.filedialog as filedialog
from pathlib import Path
from tkinter import *
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
import _thread
import queue
import tkinter as tk
import platform
import time


PATH_PREFIX = ""  # "D:\\code_local\\20200414\\305314\\"
DESCRIPTION_FILE_NAME = "commit_msg.txt"
DESCRIPTION_FILE_PATH = ""  # "C:\\Users\\xxx\\Desktop\\comment.txt"
P4_CLIENT_ROOT_KEY = "Client root"

PATH_OLD_PREFIX = ""  # PATH_PREFLIX + "old\\"
PATH_NEW_PREFIX = ""  # PATH_PREFLIX + "new\\"
P4_PROJECT_PATH_PREFIX = ""  # 
P4_CLIENT_ROOT_PATH = ""  # D:\\jdm_p4_workspace\\"
BEYOND_COMPARE_PATH = ""#"\"C:\\Program Files (x86)\\Beyond Compare 3\\BCompare.exe\""

old_files = []
new_files = []
old_files_tmp = []
new_files_tmp = []
conflict_files = []
old_conflict_files = []
new_conflict_files = []
dest_conflict_files = []
merged_files = []
perforce_dst_file_path = []
platform_flag = ""

logger = logging.getLogger(__name__)


# a = os.system(r"p4 info")

class QueueHandler(logging.Handler):
    """Class to send logging records to a queue
    It can be used from different threads
    The ConsoleUi class polls this queue to display records in a ScrolledText widget
    """

    # Example from Moshe Kaplan: https://gist.github.com/moshekaplan/c425f861de7bbf28ef06
    # (https://stackoverflow.com/questions/13318742/python-logging-to-tkinter-text-widget) is not thread safe!
    # See https://stackoverflow.com/questions/43909849/tkinter-python-crashes-on-new-thread-trying-to-log-on-main-thread

    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(record)


def readfile(file):
    with open(file) as file_obj:
        content = file_obj.read()
        print(content)
        return content


def resetdata():
    old_files.clear()
    new_files.clear()
    old_files_tmp.clear()
    new_files_tmp.clear()
    conflict_files.clear()
    old_conflict_files.clear()
    new_conflict_files.clear()
    dest_conflict_files.clear()
    merged_files.clear()
    perforce_dst_file_path.clear()


def list_all_files(rootdir):
    import os
    _files = []

    # 列出文件夹下所有的目录与文件
    list_file = os.listdir(rootdir)

    for i in range(0, len(list_file)):

        # 构造路径
        path = os.path.join(rootdir, list_file[i])

        # 判断路径是否是一个文件目录或者文件
        # 如果是文件目录，继续递归

        if os.path.isdir(path):
            _files.extend(list_all_files(path))
        if os.path.isfile(path):
            _files.append(path)
    return _files




# generate new changelist
def generate_change_list():
    p4_change_cmd = "p4 change -i < " + DESCRIPTION_FILE_PATH
    logger.debug("generate change list begin,%s", p4_change_cmd)
    resp = os.popen(p4_change_cmd).readlines()
    try:
        pending_id = re.findall("\d+", resp[0])[0]
    except:
        logger.error("generate change list failed, check command %s", p4_change_cmd)
        return 0

    logger.info("change list id：%s", pending_id)
    logger.debug("generate change list end")
    return pending_id


# resp = os.popen('p4 change').readlines()
# print(resp)
# m = re.findall("\d+", resp[0])[0]
# print(m)


# print("Sync perforce codes...\n")
# os.popen('p4 change')

def getp4projectpath(prefix, file):
    logger.info("getp4projectpath prefix：%s, file is %s", prefix, file)
    path = file
    path = path.replace(prefix, P4_PROJECT_PATH_PREFIX)
    path = path.replace('\\', '/')
    logger.debug("p4 project path %s", path)
    perforce_dst_file_path.append(path)
    return path


def getp4clientpath(project_dst_path):
    if platform_flag == 1:
        client_dst_path = project_dst_path.replace("//", "\\")
        client_dst_path = client_dst_path.replace("/", "\\")
    elif platform_flag == 2:
        client_dst_path = project_dst_path.replace("//", "/")

    client_dst_path = P4_CLIENT_ROOT_PATH + client_dst_path

    return client_dst_path


def precheckfileindepth(path):
    # check file exist, check file
    if not checkfileexist(path):
        logger.error("file not exist, please check file path: %s", path)
        return False

    # check file in change list
    if checkfileinchangelist(pending_id, path):
        logger.debug("file already checked out")
        return False

    return True


def p4add2(files, pending_id):
    for i in range(0, len(files)):
        path = files[i]
        path = path.replace(PATH_OLD_PREFIX, P4_PROJECT_PATH_PREFIX)
        path = path.replace('\\', '/')
        logger.debug(path)
        perforce_dst_file_path.append(path)
        p4_sync_cmd = "p4 sync --parallel=0 " + path + "#0"
        resp = os.popen(p4_sync_cmd).readlines()
        path_cmd = "p4 edit -c " + pending_id + " " + path
        logger.debug(path_cmd)
        resp = os.popen(path_cmd).readlines()


def p4edit(path, pending_id):
    p4_sync_cmd = "p4 sync " + path + "#none"
    # p4_sync_cmd = "p4 sync --parallel=0 " + path + "#none"
    p4_sync_cmd = "p4 sync " + path + "#head"
    resp = os.popen(p4_sync_cmd).readlines()
    path_cmd = "p4 edit -c " + pending_id + " " + path
    logger.debug(path_cmd)
    resp = os.popen(path_cmd).readlines()

    for line in resp:
        if len(line.strip()) != 0:
            logger.debug(line)
            if line.find("can't change from change") >= 0:
                logger.critical("Check the file status %s ", path)
                return False

    return True


def p4delete(path, pending_id):
    p4_delete_cmd = "p4 delete -c " + pending_id + " -v " + path
    logger.debug(p4_delete_cmd)
    resp = os.popen(p4_delete_cmd).readlines()

    for line in resp:
        if len(line.strip()) != 0:
            logger.debug(line)


def p4add(file, path, pending_id):
    copy_cmd = "copy /Y " + file + " " + path
    logger.debug(copy_cmd)
    resp = os.popen(copy_cmd).readlines()
    p4_add_cmd = "p4 add -d -c " + pending_id + " " + path
    logger.debug(p4_add_cmd)
    resp = os.popen(p4_add_cmd).readlines()

    for line in resp:
        if len(line.strip()) != 0:
            logger.debug(line)


def replace_file():
    copy_cmd = "copy "


def getfiles():
    global old_files, new_files, i
    old_files = list_all_files(PATH_OLD_PREFIX)
    new_files = list_all_files(PATH_NEW_PREFIX)
    logger.info("%d files in total ", len(old_files))
    for i in range(0, len(old_files)):
        path = old_files[i]
        # logger.debug("old path: %s", path)
        path = path.replace(PATH_OLD_PREFIX, '')
        # print(path)

        old_files_tmp.append(path)
    for i in range(0, len(new_files)):
        path = new_files[i]
        # logger.debug("new path: %s", path)
        path = path.replace(PATH_NEW_PREFIX, '')
        # print(path)

        new_files_tmp.append(path)


def shave_change(pending_id):
    shave_cmd = "p4 shelve -f -a leaveunchanged -c " + pending_id
    resp = os.popen(shave_cmd).readlines()
    print(resp)


def mergechange(pending_id):
    logger.debug("mergechange start")
    global i, project_dst_path, fc_result, copy_cmd, resp
    for i in range(0, len(old_files_tmp)):
        count = new_files_tmp.count(old_files_tmp[i])
        if count > 0:
            index = new_files_tmp.index(old_files_tmp[i])
            project_dst_path = getp4projectpath(PATH_NEW_PREFIX, new_files[index])
            if not checkfileexist(project_dst_path):
                logger.error("file not exist, please check file path: %s", project_dst_path)
                return False
            if checkfileinchangelist(pending_id, project_dst_path):
                logger.debug("file already checked out")
            else:
                res = p4edit(project_dst_path, pending_id)
                if not res:
                    continue

            # project_dst_path = project_dst_path.replace("//", "\\")
            # project_dst_path = project_dst_path.replace("/", "\\")
            # project_dst_path = P4_CLIENT_ROOT_PATH + project_dst_path
            client_dst_path = getp4clientpath(project_dst_path)
            fc_result = fc.cmp(old_files[i], client_dst_path, shallow=False)
            if fc_result:
                copy_cmd = "copy /Y " + new_files[index] + " " + client_dst_path
                # print(copy_cmd)
                resp = os.popen(copy_cmd).readlines()
                merged_files.append(old_files_tmp[i])
                logger.info("file merged sucess, file path: %s", project_dst_path)
            else:
                # check if it is latest version already
                fc_result = fc.cmp(new_files[index], client_dst_path, shallow=False)
                if fc_result:
                    logger.info("already latest file, ingored, file path: %s", project_dst_path)
                else:
                    logger.info("conflict_files, need check, file path: %s", project_dst_path)
                    conflict_files.append(old_files_tmp[i])
                    old_conflict_files.append(old_files[i])
                    new_conflict_files.append(new_files[i])
                    dest_conflict_files.append(client_dst_path)
        else:
            # for delete
            logger.debug("start delete file")
            project_dst_path = getp4projectpath(PATH_OLD_PREFIX, old_files[i])
            p4delete(project_dst_path, pending_id)
            merged_files.append(old_files_tmp[i])
            logger.info("file delete sucess, file path: %s", project_dst_path)

    for i in range(0, len(new_files_tmp)):
        count = old_files_tmp.count(new_files_tmp[i])
        if count > 0:
            # logger.debug("already handle")
            print("already handle")
        else:
            # for add
            logger.debug("start add file")
            project_dst_path = getp4projectpath(PATH_NEW_PREFIX, new_files[i])
            client_dst_path = getp4clientpath(project_dst_path)
            #check file exist or not
            if checkfileexist(client_dst_path):
                logger.info("file already exist %s", client_dst_path)
            p4add(new_files[i], client_dst_path, pending_id)
            merged_files.append(new_files_tmp[i])
            logger.info("file add sucess, file path: %s", project_dst_path)
    if len(conflict_files) > 0:
        logger.info("you have to merge the code manually...")
        for i in range(len(conflict_files)):
            # print("file path: ", conflict_files[i])
            logger.critical("need merge file: %s", conflict_files[i])
            if platform_flag == 1:
                bc_cmd = BEYOND_COMPARE_PATH + " " + new_conflict_files[i] + " " + old_conflict_files[i]
                logger.info(bc_cmd)
                resp = os.popen(bc_cmd).readlines()
                #time.sleep(0.1)
                bc_cmd = BEYOND_COMPARE_PATH + " " + new_conflict_files[i] + " " + dest_conflict_files[i]
                logger.info(bc_cmd)
                resp = os.popen(bc_cmd).readlines()

    logger.info("**********The End**********\r\n\r\n")


def getp4info():
    logger.info("getting p4 info...")
    p4_info_cmd = "p4 info "
    resp = os.popen(p4_info_cmd).readlines()
    for line in resp:
        line = line.strip()
        client_index = line.find(P4_CLIENT_ROOT_KEY)
        if client_index >= 0:
            global P4_CLIENT_ROOT_PATH
            P4_CLIENT_ROOT_PATH = line[client_index + len(P4_CLIENT_ROOT_KEY) + 2:].strip()
            logger.debug("P4_CLIENT_ROOT_PATH is: %s", P4_CLIENT_ROOT_PATH)
            break


def checkfileexist(file):
    have_file_cmd = "p4 files " + file
    logger.debug("have_file_cmd : %s", have_file_cmd)
    resp = os.popen(have_file_cmd).readlines()
    for line in resp:
        if len(line.strip()) != 0:
            if line.find("no such file") >= 0:
                return False
            else:
                return True


def checkfoldexist(path):
    # if rootdir.is_dir():
    rootdir = Path(path)
    if rootdir.is_dir():
        return True
    else:
        return False


def getplatform():
    global platform_flag
    if platform.system() == 'Windows':
        platform_flag = 1
    elif platform.system() == 'Linux':
        platform_flag = 2


def checkfileinchangelist(changelist, file):
    opend_cmd = "p4 opened -c " + changelist + " " + file
    logger.debug("opend_cmd %s", opend_cmd)
    resp = os.popen(opend_cmd).readlines()

    if len(resp) > 0:
        return True
    else:
        return False

def cmp_lines(path_1, path_2):
    l1 = l2 = True
    with open(path_1, 'r') as f1, open(path_2, 'r') as f2:
        while l1 and l2:
            l1 = f1.readline()
            l2 = f2.readline()
            if l1 != l2:
                return False
    return True

def choose_file_callback():
    entry.delete(0, END)
    global filepath
    filepath = filedialog.askdirectory()
    if not filepath.endswith('/'):
        filepath = filepath + "/"
    filepath = filepath.replace('/', '\\')
    if filepath:
        entry.insert(0, filepath)


def init_variable():
    global PATH_PREFIX, PATH_OLD_PREFIX, PATH_NEW_PREFIX, DESCRIPTION_FILE_PATH,BEYOND_COMPARE_PATH
    PATH_PREFIX = filepath

    if platform_flag == 1:
        PATH_OLD_PREFIX = PATH_PREFIX + "old\\"
        PATH_NEW_PREFIX = PATH_PREFIX + "new\\"
        if not bc_path.endswith('\"'):
            BEYOND_COMPARE_PATH = "\"" + bc_path + "\""
        else:
            BEYOND_COMPARE_PATH = bc_path

        pwd_cmd = "cd"
    elif platform_flag == 2:
        PATH_PREFIX = filepath.replace('\\', '/')
        PATH_OLD_PREFIX = PATH_PREFIX + "old/"
        PATH_NEW_PREFIX = PATH_PREFIX + "new/"
        pwd_cmd = "pwd"

    resp = os.popen(pwd_cmd).readline()

    if platform_flag == 1:
        DESCRIPTION_FILE_PATH = resp.strip('\n') + "\\" + DESCRIPTION_FILE_NAME
    elif platform_flag == 2:
        DESCRIPTION_FILE_PATH = resp.strip('\n') + "/" + DESCRIPTION_FILE_NAME


    logger.debug("old folder is:%s", PATH_OLD_PREFIX)
    logger.debug("new folder is:%s", PATH_NEW_PREFIX)
    logger.debug("DESCRIPTION_FILE is:%s", DESCRIPTION_FILE_PATH)


def handle(i):
    getp4info()
    global pending_id
    if (len(pending_id_entry.get()) > 0):
        pending_id = pending_id_entry.get()
        logger.info("append to the pending id :%s", pending_id)
    else:
        pending_id = generate_change_list()
        if(pending_id == 0):
            return
    getfiles()
    mergechange(pending_id)


def start_apply():
    global filepath, path, bc_path
    path = path_entry.get()
    bc_path = bc_entry.get()
    if (len(path) <= 0):
        messagebox.showinfo(title='Warning', message='请输入导入路径')
        return
    if (len(filepath) <= 0):
        messagebox.showinfo(title='Hi', message='请选择文件')
        return

    logger.debug("path is:%s", path)
    logger.debug("filepath is:%s", filepath)

    resetdata()
    init_variable()

    logger.debug("filepath is:%s", filepath)

    if not checkfoldexist(PATH_OLD_PREFIX) or not checkfoldexist(PATH_NEW_PREFIX):
        logger.error("please check your folder:%s, %s", PATH_OLD_PREFIX, PATH_NEW_PREFIX)
        messagebox.showinfo(title='Warning', message='请检查文件路径下是否包含new,old文件夹')
        return False
    else:
        global P4_PROJECT_PATH_PREFIX
        if path.endswith('/'):
            P4_PROJECT_PATH_PREFIX = path
        else:
            P4_PROJECT_PATH_PREFIX = path + "/"

        _thread.start_new_thread(handle, (2,))


def setuploginfo(debugflag):
    if debugflag:
        logging.getLogger().setLevel(logging.DEBUG)
        # logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s')
    else:
        logging.getLogger().setLevel(logging.INFO)
        # logging.basicConfig(level=logging.INFO, format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s')


def display(record):
    msg = queue_handler.format(record)
    scrolled_text.configure(state='normal')
    scrolled_text.insert(tk.END, msg + '\n', record.levelname)
    scrolled_text.configure(state='disabled')
    # Autoscroll to the bottom
    scrolled_text.yview(tk.END)


def poll_log_queue():
    # Check every 100ms if there is a new message in the queue to display
    while True:
        try:
            record = log_queue.get(block=False)
        except queue.Empty:
            break
        else:
            display(record)
    root.after(100, poll_log_queue)


def debug_click():
    # Check every 100ms if there is a new message in the queue to display
    if var_debug.get() == 1:
        setuploginfo(True)
    else:
        setuploginfo(False)


def maingui():
    global entry, root, listbox_filename, filepath, path, log_queue, queue_handler, scrolled_text, var_debug
    root = Tk()
    root.title("Patch Apply")
    root.geometry("900x900")
    root.rowconfigure(1, weight=1)
    root.rowconfigure(2, weight=8)
    filepath = ""
    path = ""
    l = Label(root, bg='yellow', width=20, text='empty')

    entry = Entry(root, width=60)
    entry.grid(sticky=W + N, row=0, column=0, columnspan=4, padx=5, pady=5)

    button = Button(root, text="选择文件夹", command=choose_file_callback)
    button.grid(sticky=W + N, row=1, column=0, padx=5, pady=5)

    Label(root, text='导入路径: ').place(x=10, y=80)
    global path_entry
    path_entry = Entry(root, width=200)
    path_entry.place(x=120, y=80)
    Label(root,
          text='导入路径示例：      //PROD_QUEEN/ONEUI_2_1/FLUMEN/Waffle/MT6765/android/vendor/mediatek/proprietary/custom/').place(
        x=10, y=110)

    Label(root, text='PendingList').place(x=10, y=135)
    global pending_id_entry
    pending_id_entry = Entry(root, width=40)
    pending_id_entry.place(x=120, y=135)

    Label(root, text='Beyond Compare: ').place(x=10, y=160)
    global bc_entry
    bc_entry = Entry(root, width=200)
    bc_entry.place(x=120, y=160)
    bc_entry.insert(10, "C:\\Program Files (x86)\\Beyond Compare 3\\BCompare.exe")

    btn_comfirm = Button(root, text='确定', command=start_apply)
    btn_comfirm.place(x=420, y=185)

    var_debug = IntVar()
    Checkbutton(root, text='debug', variable=var_debug, command=debug_click).place(x=10, y=255)
    scrolled_text = ScrolledText(root, state='disabled', height=45, width=215)
    scrolled_text.grid(row=0, column=0, sticky=(N, S, W, E))
    scrolled_text.configure(font='TkFixedFont')
    scrolled_text.tag_config('INFO', foreground='black')
    scrolled_text.tag_config('DEBUG', foreground='gray')
    scrolled_text.tag_config('WARNING', foreground='orange')
    scrolled_text.tag_config('ERROR', foreground='red')
    scrolled_text.tag_config('CRITICAL', foreground='red', underline=1)
    scrolled_text.place(x=10, y=280)

    # Create a logging handler using a queue
    log_queue = queue.Queue()
    queue_handler = QueueHandler(log_queue)
    formatter = logging.Formatter(
        '%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s')  # %(asctime)s: %(message)s'
    queue_handler.setFormatter(formatter)
    logger.addHandler(queue_handler)
    # Start polling messages from the queue
    root.after(100, poll_log_queue)

    root.mainloop()


if __name__ == "__main__":
    # execute only if run as a script
    getplatform()
    resetdata()
    setuploginfo(False)
    maingui()
