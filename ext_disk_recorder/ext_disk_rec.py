import os, sys, threading, time, psutil, subprocess, logging
sys.path.append(os.path.dirname(__file__))
import com_main_module, ext_slarchive

class MAIN_MODULE_CLASS(com_main_module.COMMON_MAIN_MODULE_CLASS):
    def __init__(self, njsp, trigger_fxn, standalone = False):
        logger_config = {
            'logger_name':'ext_disk_recorder',
            'file_name':'ext_disk_recorder',
            'files_dir':'/media/sdcard/logs',
            'file_level': logging.INFO,
            'console_level': logging.DEBUG,# if standalone else logging.WARN,
            'console_name': None if standalone else 'EXT_RECORD'
        }
        config_params = { 
            "config_file_name":'ext_disk_recorder.json',
            "default_config": {
                "seedlink_addr": 'localhost:18000',
                "start_immediately":False
            }
        }
        super().__init__(standalone, config_params, njsp, logger_config, trigger_fxn = trigger_fxn)
        self.logger.info("Starting External disk recorder module...")
        

    def main(self):
        self.logger.debug("Main thread started")
        self.state = 'no_disk'
        self.message = 'No disk'
        self.led_set()
        if self.config.error == 'Error reading config file, defaults used': 
            self.config.set_config(self.config.cfg)
        self.slarchive = ext_slarchive.SLARCHIVE(self.logger, self.config.cfg)
        self.errors = self.slarchive.errors

        while self.shutdown_event.is_set() == False:
            time.sleep(1)
            self.__scan_disks()
            if self.state == 'disk_ok_writing': self.led_set(red = 't')

        self.state_machine('disk_must_be_ejected')  
        self.module_alive = False
        self.logger.debug("Main thread exited")
        
    def led_set(self, red = 'c', green = 'c'):
        self.trigger.relay("usr_out_1",red)
        self.trigger.relay("usr_out_2",green)
        self.trigger.fire()
        
    def state_machine(self, new_state, device='', mountpt=''):
        if self.state == new_state: return
        self.logger.debug("Switching from state %s to %s"%(self.state, new_state))
    
        if self.state == 'no_disk':
            pass
        elif self.state == 'disk_ok_waiting':
            pass
        elif self.state == 'disk_ok_writing':
            self.logger.info("Finishing recording")
            self.slarchive.stop()
        elif self.state == 'disk_must_be_ejected':
            pass
            
        if new_state == 'no_disk':
            self.logger.warning("USB drive %s removed"%self.dev)
            self.dev = ''
            self.mount_pt = ''
            self.led_set()
            self.message = 'No disk'
        elif new_state == 'disk_ok_waiting':
            self.logger.info("USB drive %s detected, mounted on %s"%(device, mountpt))
            self.dev = device
            self.mount_pt = mountpt
            self.led_set(green = 's')
            self.message = 'Disk OK, waiting command'
        elif new_state == 'disk_ok_writing':
            self.logger.info("Starting recording")
            self.slarchive.run(self.mount_pt)
            self.message = 'Writing in progress...'
        elif new_state == 'disk_must_be_ejected':
            self.logger.warning("Ejecting disk...")
            self.led_set()
            self.__unmount()
    
        self.state = new_state
        
    def process_user_input(self, channel, state):
        if channel == 'button1':
            if self.state == 'no_disk': self.logger.warning("Button pressed but disk not found")
            elif self.state == 'disk_ok_waiting': self.state_machine('disk_ok_writing')
            elif self.state == 'disk_ok_writing': self.state_machine('disk_must_be_ejected')
        
    def __unmount(self):
        if self.mount_pt != '': 
            while True:
                run_res = subprocess.run(['sudo', 'umount', self.mount_pt], universal_newlines=True)
                if run_res.stdout != None: self.logger.error(run_res.stdout)
                elif run_res.returncode != 0: self.logger.error('Umount returned code %d'%run_res.returncode)
                else: break
                time.sleep(0.3)
        
    def __scan_disks(self):
        disk_present = False
        for disk in psutil.disk_partitions():
            if str(disk.device).find('sda') != -1: 
                if self.state == 'no_disk':
                    self.state_machine('disk_ok_waiting', device=disk.device, mountpt=disk.mountpoint)
                    if self.config.cfg['start_immediately']: self.state_machine('disk_ok_writing')
                disk_present = True
                break
        if not disk_present and self.state != 'no_disk': self.state_machine('no_disk')
                
