# libraries
from evdev import InputDevice

# loop through devices
for i in range(20):
    try:
        # print device data
        devFind = str(InputDevice('/dev/input/event' + str(i)))
        devData = devFind.split(',')
        print(devData)
    except:
        # prevent errors
        break
