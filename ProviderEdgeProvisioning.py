from distutils.sysconfig import customize_compiler
import aiohttp
import asyncio
import xml
import requests
import json
from aiohttp.helpers import BasicAuth


class MplsPe():
    def __init__(self,HostName, MgmtIp, UserName, Password):
        self.HostName = HostName
        self.MgmtIp = MgmtIp
        self.UserName = UserName
        self.Password = Password
    
    def GetConfig(self):
        headers = {'Accept': 'application/yang-data+json'}
        result = requests.get(url=f"https://{self.MgmtIp}/restconf/data/Cisco-IOS-XE-native:native/",auth=(self.UserName,self.Password),verify=False,headers=headers).text
        return result

    def CreateVRF(self):
        CustomerName = 'whitespdier'
        CustomerID = '2'
        VpnId = '10'
        headers = {'Accept': 'application/yang-data+json','content-type':'application/yang-data+json'}
        payload = {
    "Cisco-IOS-XE-native:vrf": [
        {
            "name": f"cust-vrf-{CustomerName}",
            "rd": f'{CustomerID}:{VpnId}',
            "route-target": [
                {
                    "direction": "export",
                    "target": f'{CustomerID}:{VpnId}'
                },
                {
                    "direction": "import",
                    "target": f'{CustomerID}:{VpnId}'
                }
            ]
        }
    ]
}

        print (payload)

        result = requests.patch(url=f"https://{self.MgmtIp}/restconf/data/Cisco-IOS-XE-native:native/ip/vrf",auth=(self.UserName,self.Password),verify=False,headers=headers,data=json.dumps(payload)).text
        return result


r1 = MplsPe('pe1','192.168.137.200','craig','Telecaster1!')

print (r1.GetConfig())
print (r1.CreateVRF())