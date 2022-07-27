#! /usr/bin/python3

import os, sys, signal, traceback
module_dir = os.path.dirname(__file__)
print("Module running from %s" %module_dir)
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(module_dir)), 'common'))
import ext_disk_rec

print("Starting standalone, PID:%d..."%os.getpid())

ext_disk_rec = ext_disk_rec.MAIN_MODULE_CLASS(None, None, standalone = True)

def sigint_handler(sig, frame):
    print('You pressed Ctrl+C!')
#    siguser2_handler(sig, frame)
    ext_disk_rec.shutdown_event.set()
    
def siguser1_handler(sig, frame):
    for worker in workers_list: worker.dbg_print_enable(5)
    
def siguser2_handler(sig, frame):
    lines = ''
    lines += "*** STACKTRACE - START ***\n"
    code = []
    for threadId, stack in sys._current_frames().items():
        code.append("\n# ThreadID: %s\n" % threadId)
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s\n' % (filename, lineno, name))
            if line: code.append("  %s\n" % (line.strip()))
    for line in code: lines += line
    lines += "*** STACKTRACE - FINISH ***\n"
    print(lines)
    
signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGUSR1, siguser1_handler)
signal.signal(signal.SIGUSR2, siguser2_handler)

