from time import sleep
from aiohttp.helpers import BasicAuth
import ipaddress
import aiohttp
import asyncio
import requests
import json
import crayons
import os
from configparser import ConfigParser

###################
# Config Read     #
###################
config_object = ConfigParser()
config_object.read("config.ini")
userinfo = config_object["new-customer"]

CustomerName = userinfo['CustomerName']
CustomerID = userinfo['CustomerID']
VpnId = userinfo['VpnId']

######################
# Provision          #
######################


class MplsPe():
    def __init__(self, HostName, MgmtIp, UserName, Password):
        self.HostName = HostName
        self.MgmtIp = MgmtIp
        self.UserName = UserName
        self.Password = Password
        self.headers = {'Accept': 'application/yang-data+json',
                        'Content-Type': 'application/yang-data+json'}

    def GetConfig(self):
        result = requests.get(url=f"https://{self.MgmtIp}/restconf/data/Cisco-IOS-XE-native:native/", auth=(
            self.UserName, self.Password), verify=False, headers=self.headers).text
        return result

    async def CreateVRF(self):
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
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False, limit_per_host=10), headers=self.headers) as session:
            async with session.patch(url=f"https://{self.MgmtIp}/restconf/data/Cisco-IOS-XE-native:native/ip/vrf",
                                     auth=aiohttp.BasicAuth(self.UserName, self.Password), data=json.dumps(payload)) as response:
                resp = await response.text()
                print('Actioning {}:        Creating VRF for {}'.format(
                    self.HostName, CustomerName))
                print('     '+crayons.green(response.status))

        return resp

    async def UpdateMpBGP(self):
        payload = {
            "Cisco-IOS-XE-bgp:vrf": [
                {
                    "name": f"cust-vrf-{CustomerName}",
                    "ipv4-unicast": {
                        "redistribute-vrf": {
                            "connected": {},
                            "static": {}
                        }
                    }
                }
            ]
        }
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False, limit_per_host=10), headers=self.headers) as session:
            async with session.patch(url=f"https://{self.MgmtIp}/restconf/data/Cisco-IOS-XE-native:native/router/Cisco-IOS-XE-bgp:bgp=65010/address-family/with-vrf/ipv4=unicast/vrf", auth=aiohttp.BasicAuth(self.UserName, self.Password), data=json.dumps(payload)) as response:
                resp = await response.text()
                print('Actioning {}:        Creating IPv4 ADF for {}'.format(
                    self.HostName, CustomerName))
                print('     '+crayons.green(response.status))

        return resp

    async def ProvisionServiceInterface(self):

        # print(f'srv interface for {self.HostName}')
        f = open('ipam.json', 'r+')

        ##################################################
        # REFACTOR? / SEPERATE DB READ/WRITE FUNCTION???
        ###################################################

        conn = json.load(f)
        for x in conn['customer-peering-addresses']:
            if not x['customer']:
                # print(x)
                x['customer'] = CustomerName
                break
        os.remove('ipam.json')
        f = open('ipam.json', 'w')
        json.dump(conn, f, indent=4)
        f.close()
        ###################################################

        ##################################################
        # Refactor? / Get Service Interface IP and Mask
        ###################################################
        ip_addr = str(x['net'])+'/'+str(x['mask'])
        assignablehosts = ipaddress.IPv4Network(ip_addr).hosts()
        addrlist = list(assignablehosts)
        netstring = ipaddress.IPv4Network(
            str(x['net']+'/'+str(x['mask']))).with_netmask
        ###################################################
        payload = {
            "Cisco-IOS-XE-native:interface": {
                "GigabitEthernet": [
                    {
                        "name": f"3.{CustomerID}",
                        "encapsulation": {
                            "dot1Q": {
                                "vlan-id": int(CustomerID)
                            }
                        },
                        "ip": {
                            "vrf": {
                                "forwarding": {
                                    "word": f"cust-vrf-{CustomerName}"
                                }
                            },
                            "address": {
                                "primary": {
                                    "address": str(addrlist[0]),
                                    "mask": netstring.split('/')[1]
                                }
                            }
                        }
                    }
                ]
            }}

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False, limit_per_host=10), headers=self.headers) as session:
            async with session.patch(url=f"https://{self.MgmtIp}/restconf/data/Cisco-IOS-XE-native:native/interface", auth=aiohttp.BasicAuth(self.UserName, self.Password), data=json.dumps(payload)) as response:
                resp = await response.text()

                print('Actioning {}:        Service Interface For {}'.format(
                    self.HostName, CustomerName))
                print('     '+crayons.green(response.status))

        return resp


async def main():
    r1 = MplsPe('pe1', '192.168.137.200', 'craig', 'pa55w0rd1!')
    r2 = MplsPe('pe2', '192.168.137.201', 'craig', 'pa55w0rd1!')
    r3 = MplsPe('pe3', '192.168.137.202', 'craig', 'pa55w0rd1!')
    edges = [r1, r2, r3]

    for x in edges:
        vrfTask = asyncio.create_task(x.CreateVRF())

    await asyncio.gather(vrfTask)

    await asyncio.sleep(1)

    for x in edges:
        bgptask = asyncio.create_task(x.UpdateMpBGP())

    await asyncio.gather(bgptask)

    await asyncio.sleep(3)

    for x in edges:
        provision = asyncio.create_task(x.ProvisionServiceInterface())

    await asyncio.gather(provision)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
