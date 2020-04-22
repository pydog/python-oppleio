from . import const, OppleDevice
import datetime
import time
from threading import Thread

MESSAGE_TYPE     = const.MESSAGE_TYPE
QUERY_RES_OFFSET = const.QUERY_RES_OFFSET

OppleLightDevices = []

class OppleLightDevice(OppleDevice.OppleDevice):
    def __init__(self, ip='', message=None):
        self._isPowerOn = False
        self._brightness = 0
        self._colorTemperature = 0
        
        super().__init__(ip, message)


    def init(self, message):
        super(OppleLightDevice, self).init(message)
        self.update()

        #print("pydog", datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S'), "init called", self.ip)
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
        #print("pydog", datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S'), "update called", self.ip)
        if not self.is_init:
            self.async_init()

        if not self.is_init:
            return

        update_thread = Thread(target=self.update_with_device, name="update status with device")
        update_thread.start()


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
                    device["is_init"] = self.is_init
                    device["is_online"] = self.is_online
                    device["isPowerOn"] = self._isPowerOn
                    device["brightness"] = self._brightness
                    device["colorTemperature"] = self._colorTemperature
                    device["last_update"] = datetime.datetime.now()
                    device["query_update"] = True
                    break
        
        end = datetime.datetime.now()
        #print("pydog", datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S'), "update device status done in", (end - start).seconds, self.ip)
        
        # query more than 2 minutes will be set be offline
        if (end - start).seconds > 120:
            device["is_online"] = False
            self.is_online = False


    def set(self, message_type, value, check=None, _time=3):
        if _time == 0:
            return False

        if check():
            return True

        set_thread = Thread(target=self.set_device, name="set device status",args=(message_type, value))
        set_thread.start()

        return True

    def set_device(self, message_type, value):
        self.send(message_type, value)
        self.update()

        for device in OppleLightDevices:
            if self.ip == device["ip"]:
                break;

        # send cmd to set status until query updated
        while not device["query_update"]:
            self.send(message_type, value)
            self.update()
            time.sleep(0.5)

        print("pydog", datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S'), "query updated", message_type)

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

        for device in OppleLightDevices:
            if self.ip == device["ip"]:
                    device["isPowerOn"] = (value == 1)

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

        for device in OppleLightDevices:
            if self.ip == device["ip"]:
                    device["brightness"] = value

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

        for device in OppleLightDevices:
            if self.ip == device["ip"]:
                    device["colorTemperature"] = value
