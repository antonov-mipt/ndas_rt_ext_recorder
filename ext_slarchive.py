import subprocess, os, threading, time, select, signal

class SLARCHIVE:
    def __init__(self, logger, config):
        self.logger = logger.create_child_adapter('SLARCHIVE')
        self.errors = list()
        self.path_to_executable = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'slarchive')
        self.addr = config['seedlink_addr']
        self.can_run = False
        self.must_be_running = False
        self.sigint_timeout = 3
        if os.path.isfile(self.path_to_executable) == False: self.__err('No slarchive binary')
        else: self.can_run = True
        
    def __err(self, err):
        if err not in self.errors: self.errors.append(err)
        self.logger.error(err)
            
    def run(self, target_path):
        if not self.can_run or self.must_be_running: return
        if os.path.exists(target_path) == False: 
            self.__err('Path %s does not exists'%target_path)
            return
        
        params = [self.path_to_executable, self.addr, '-SDS', target_path, '-k', '300']
        self.slarchive_process = subprocess.Popen(params, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        time.sleep(0.3)
        if self.slarchive_process.poll() == None:
            self.must_be_running = True
            self.logger.info("Slarchive executable started")
            self.sl_arch_thread = threading.Thread(target=self.__slarchive_poller, args=([params]))
            self.sl_arch_thread.start()
        else:
            self.logger.critical('Slarchive executable did not start')

    def stop(self):
        self.must_be_running = False
        self.logger.warning("Sending ctrl+c signal to slarchive...")
        start_wait_time = time.monotonic()
        self.slarchive_process.send_signal(signal.SIGINT)
        retval = self.slarchive_process.wait(self.sigint_timeout)
        if retval == None: 
            self.logger.error("Slarchive did not stop in %d sec, killing"%self.sigint_timeout)
            self.slarchive_process.kill()
        else:
            self.logger.debug("Slarchive stoppend in %d ms"%((time.monotonic()-start_wait_time)*1000))
        self.sl_arch_thread.join()
        
    def __print_stdout(self, line, prefix):
        text = line.decode('utf-8')
        if len(text)>0: 
            lines = text.split('\n')
            for line in lines: 
                if len(line)> 0: self.logger.info(prefix + line)
                
    def __print_stderr(self, line, prefix):
        text = line.decode('utf-8')
        if len(text)>0: 
            lines = text.split('\n')
            for line in lines: 
                if len(line)> 0: self.logger.error(prefix + line)
    
    def __slarchive_poller(self, params):
        p = self.slarchive_process
        while p.poll() == None:
            r, w, e = select.select([ p.stdout, p.stderr ], [], [], 0.5)
            if p.stdout in r: 
                #try: 
                self.__print_stdout(p.stdout.readline(), '[STDOUT] ')
                #except: pass
            if p.stderr in r: 
                #try: 
                self.__print_stderr(p.stderr.readline(), '[STDERR] ')
                #except: pass
        
        msg = "Slarchive executable exited"
        if self.must_be_running: self.__err(msg)
        else: self.logger.info(msg)
        