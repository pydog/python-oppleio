from . import const, OppleDevice
import datetime
import time
import threading

MESSAGE_TYPE     = const.MESSAGE_TYPE
QUERY_RES_OFFSET = const.QUERY_RES_OFFSET

OppleLightDevices = []

class OppleLightDevice(OppleDevice.OppleDevice):
    def __init__(self, ip='', message=None):
        self._isPowerOn = False
        self._brightness = 0
        self._colorTemperature = 0
        
        self.update_thread_max = threading.BoundedSemaphore(100)
        self.update_thread_list = []

        self.set_thread_max = threading.BoundedSemaphore(100)
        self.set_thread_list = []

        super().__init__(ip, message)


    def init(self, message):
        super(OppleLightDevice, self).init(message)
        self.update()

        new_device = {
                "ip" : self.ip, 
                "isPowerOn" : self._isPowerOn, 
                "brightness" : self._brightness, 
                "colorTemperature" : self._colorTemperature,
                "is_init" : self.is_init,
                "is_online" : self.is_online,
                "last_update" : self.last_update,
                "query_update" : False
                }

        OppleLightDevices.append(new_device)

    def update(self):
        if not self.is_init:
            self.async_init()

        if not self.is_init:
            return

        #print("pydog", datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S'), self.ip, "update thread len", len(self.update_thread_list))
        #Wait if reach to thread max
        self.update_thread_max.acquire()

        update_thread = threading.Thread(target=self.update_with_device, name="update status with device")
        update_thread.start()
        update_thread.join(120)

        self.update_thread_list.append(update_thread)
        
        for t in self.update_thread_list:
            t.join()
            del t


    def update_with_device(self):
        start = datetime.datetime.now()
        message = self.send('QUERY', reply=True)

        # send QUERY until get reply
        while not message:
            message = self.send('QUERY', reply=True)

        if message:
            self._isPowerOn = message.get(QUERY_RES_OFFSET['POWER_ON'], 1, int)
            self._brightness = message.get(QUERY_RES_OFFSET['BRIGHT'], 1, int)
            self._colorTemperature = message.get(QUERY_RES_OFFSET['COLOR_TEMP'], 2, int)
            for device in OppleLightDevices:
                if self.ip == device["ip"]:
                    device["isPowerOn"] = self._isPowerOn
                    device["brightness"] = self._brightness
                    device["colorTemperature"] = self._colorTemperature
                    device["last_update"] = datetime.datetime.now()
                    device["query_update"] = True
                    if device["is_init"] == False:
                        device["is_init"] = self.is_init = True
                    if device["is_online"] == False:
                        device["is_online"] = self.is_online= True
                    break
        
        end = datetime.datetime.now()
        for device in OppleLightDevices:
            if self.ip == device["ip"]:
                print("pydog", datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S'), "update device status done in", (end - start).seconds, self.ip,"isPowerOn", device["isPowerOn"],"is_Online", self.is_online)
        
        # query more than 2 minutes will be set be offline
        if (end - start).seconds > 1200:
            device["is_online"] = False
            self.is_online = False

        self.update_thread_max.release()


    def set(self, message_type, value, check=None, _time=3):
        if _time == 0:
            return False

        if check():
            return True

        #print("pydog", datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S'), self.ip, "set thread len", len(self.set_thread_list))
        #Wait if reach to thread max
        self.set_thread_max.acquire()
        set_thread = threading.Thread(target=self.set_device, name="set device status",args=(message_type, value, check))
        set_thread.start()
        set_thread.join(120)

        self.set_thread_list.append(set_thread)
        for t in self.set_thread_list:
            t.join()
            del t

        return True

    def set_device(self, message_type, value, check = None):
        self.send(message_type, value)
        self.update()

        for device in OppleLightDevices:
            if self.ip == device["ip"]:
                break;

        status = check()
        # send cmd to set status until query updated
        while not device["query_update"] and not status:
            self.send(message_type, value)
            self.update()
            time.sleep(1)
            status = check()

        if message_type == "POWER_ON":
            print("pydog", datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S'), self.ip, "query updated",message_type, "isPowerOn:", device["isPowerOn"] )

        self.set_thread_max.release()

    @property
    def power_on(self):
        #print("pydog", datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S'), "request power_on status", self.ip)
        for device in OppleLightDevices:
            if self.ip == device["ip"]:
                return device["isPowerOn"]

    @power_on.setter
    def power_on(self, value):
        value = 1 if value else 0
        #print("pydog", datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S'), "set power_on", value)

        def check():
            for device in OppleLightDevices:
                if self.ip == device["ip"]:
                    device["query_update"] = False
                    return device["isPowerOn"] == (value == 1)

        self.set('POWER_ON', value.to_bytes(1, 'big'), check)

    @property
    def brightness(self):
        for device in OppleLightDevices:
            if self.ip == device["ip"]:
                return device["brightness"]

    @brightness.setter
    def brightness(self, value):
        value = max(0, value)
        value = min(255, value)

        def check():
            for device in OppleLightDevices:
                if self.ip == device["ip"]:
                    return device["brightness"] == value

        self.set('BRIGHTNESS', value.to_bytes(1, 'big'), check)

    @property
    def color_temperature(self):
        for device in OppleLightDevices:
            if self.ip == device["ip"]:
                return device["colorTemperature"]

    @color_temperature.setter
    def color_temperature(self, value):
        value = max(2700, value)
        value = min(6500, value)

        def check():
            for device in OppleLightDevices:
                if self.ip == device["ip"]:
                    return device["colorTemperature"] == value

        self.set('COLOR_TEMP', value.to_bytes(2, 'big'), check)
