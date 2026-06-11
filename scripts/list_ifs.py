from scapy.arch.windows import get_windows_if_list
import pprint
#Listing interfaces
pprint.pprint(get_windows_if_list())