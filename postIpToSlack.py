import os
import json
import socket
import ifaddr
from loguru import logger
from datetime import datetime, timezone
import time
import argparse
import SlackMessenger

import jsonpickle

PAST_IP_STORE_FILE = "ip_store.json"


class IpStore:
    def __init__(self, store_file: str = PAST_IP_STORE_FILE):
        self.store_file = store_file
        self.last_updated_time = None
        self.hostname = None
        self.interfaces_of_interest = []
        self.ips = []
        self.adapters: dict[str, ifaddr.Adapter] = {}
        self.load()

    def load(self) -> bool:
        '''Load the IP store from the store file'''
        try:
            with open(self.store_file, 'r') as f:
                data = json.load(f)
                self.last_updated_time = data.get('last_updated', None)
                self.hostname = data.get('hostname', None)
                self.interfaces_of_interest = data.get('interfaces_of_interest', [])
                self.ips = data.get('ips', [])
                adapters_json = data.get('adapters', "")
                adapter_loaded = jsonpickle.decode(adapters_json)
                # Make sure the type is correct
                if isinstance(adapter_loaded, dict):
                    self.adapters = adapter_loaded
                else:
                    self.adapters = {}
            return True
        except FileNotFoundError:
            logger.error(f"Could not find {self.store_file}")
            return False
        except json.JSONDecodeError:
            logger.error(f"Problem decoding {self.store_file}")
            return False

    def store(self) -> bool:
        '''Store the current IP addresses and associated info to the store file'''
        try:
            with open(self.store_file, 'w') as f:
                data = {
                    'last_updated': str(datetime.now()),
                    'hostname': self.hostname,
                    'interfaces_of_interest': self.interfaces_of_interest,
                    'ips': self.ips,
                    'adapters': jsonpickle.encode(self.adapters)
                }
                f.write(json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"Error storing IP data: {e}")
            return False


    def update_ips(self) -> list[bool]:
        '''Update the IPs for the interfaces of interest'''
        current_ips = []
        ip_changes = []
        adapter_changes = []
        for iface in self.interfaces_of_interest:
            iface_found = False
            for adapter in ifaddr.get_adapters():
                if adapter.name == iface or adapter.nice_name == iface:
                    # If we have not seen this interface before, then assume it has changed
                    if self.adapters.get(iface) is None:
                        adapter_changes.append(True)
                        logger.debug(f"New interface detected: {iface}")
                    # If there is a stored value for this interface, compare it to the current value
                    else:
                        if adapters_equal(self.adapters[iface], adapter):
                            adapter_changes.append(False)
                            logger.debug(f"No change detected for interface: {iface}")
                        else:
                            adapter_changes.append(True)
                            logger.debug(f"Change detected for interface: {iface}")

                    iface_found = True
                    # Update the stored adapter 
                    self.adapters[iface] = adapter

                    # Update the IP addresses in the store
                    ifaddrs = adapter.ips
                    # By default, assume no address is found
                    for ip in ifaddrs:
                        addr = "None"
                        protocol = "None"
                        if ip.is_IPv4:
                            addr = f"{ip.ip}/{ip.network_prefix}"
                            protocol = "IPv4"
                        elif ip.is_IPv6:
                            addr = f"{ip.ip}/{ip.network_prefix}"
                            protocol = "IPv6"
                        logger.debug(f"Found address for interface {iface}: {addr} ({protocol})")
                        current_ips.append({'name': iface, 'addr': addr, 'protocol': protocol})

            if not iface_found:
                logger.warning(f"Interface {iface} not found.")

        self.ips = current_ips
        return adapter_changes

def adapters_equal(adapter1: ifaddr.Adapter, adapter2: ifaddr.Adapter, check_index: bool = False) -> bool:
    if adapter1.name != adapter2.name or adapter1.nice_name != adapter2.nice_name:
        return False
    if len(adapter1.ips) != len(adapter2.ips):
        return False
    for ip1, ip2 in zip(adapter1.ips, adapter2.ips):
        if ip1.is_IPv4 != ip2.is_IPv4 or ip1.is_IPv6 != ip2.is_IPv6:
            return False
        if ip1.ip != ip2.ip or ip1.network_prefix != ip2.network_prefix or ip1.nice_name != ip2.nice_name:
            return False
    if check_index and adapter1.index != adapter2.index:
        return False
    return True

def ip_check_loop(slack_messenger: SlackMessenger.SlackMessenger, ip_store: IpStore, check_interval: int, repost_interval: int, force_send: bool):

    last_post_time = datetime.min
    
    while True:
        message_lines = []
        hostname_changes = (ip_store.hostname != socket.gethostname())
        if hostname_changes:
            message_lines.append(f"Hostname changed detected: {ip_store.hostname} -> {socket.gethostname()}")
            ip_store.hostname = socket.gethostname()

        ip_changes = ip_store.update_ips()
        any_change = any(ip_changes) or hostname_changes

        time_since_last_post = (datetime.now() - last_post_time).total_seconds()

        if any_change or (repost_interval > 0 and time_since_last_post >= repost_interval) or force_send:
            message_lines.append(f"IP Address Update for {ip_store.hostname}:")
            for ip_info in ip_store.ips:
                message_lines.append(f"- {ip_info['name']}: {ip_info['addr']}")
            message = "\n".join(message_lines)

            if slack_messenger.post_message(message):
                ip_store.store()
                last_post_time = datetime.now()
            else:
                logger.error("Failed to post IP update to Slack.")

        time.sleep(check_interval)



def main():

    parser = argparse.ArgumentParser(description="Post IP addresses to Slack")
    parser.add_argument("--config", help="Path to configuration file", default="service_config.json")
    parser.add_argument("--secrets", help="Path to secrets file", default="secrets.json")
    parser.add_argument("--force", help="Force reposting of IP addresses even if unchanged. Overrides force in config file", action="store_true")
    args = parser.parse_args()




    # Read the configuration file and setup app
    try:
        with open(args.config, "r") as f:
            service_config = json.load(f)
            service_config_log_level = service_config.get("logs", {}).get("level", "INFO").upper()
            service_config_log_directory = service_config.get("logs", {}).get("log_directory", ".")
            service_config_check_interval = service_config.get("check_interval", 3600)
            service_config_repost_interval = service_config.get("repost_interval", -1)
            service_config_force = service_config.get("force", False)
            service_config_ip_store_file = service_config.get("ip_store_file", "ip_store.json")
            # Process the interfaces of interest. 
            ioi = service_config.get('interfaces_of_interest', "all")

            if isinstance(ioi, str):
                if ioi == "all":
                    service_config_interfaces_of_interest = [adapter.name for adapter in ifaddr.get_adapters()]
                else:
                    logger.warning(f"Treating interfaces_of_interest value '{ioi}' as interface name")
                    service_config_interfaces_of_interest = [ioi]
            else:
                service_config_interfaces_of_interest = ioi

            # Ensure the log directory exists
            os.makedirs(service_config_log_directory, exist_ok=True)

            logger.remove(0)
            logger.add(f"{service_config_log_directory}/ip_poster_{{time:YYYY-MM-DD}}.log", level=service_config_log_level, rotation="sunday", retention=4)

            logger.debug("===== Starting new run of IP Poster =====")
            logger.debug("+++SETTINGS+++")
            logger.debug(f"\tLog Level: {service_config_log_level}")
            logger.debug(f"\tLog Directory: {service_config_log_directory}")
            logger.debug(f"\tRepost Interval: {service_config_repost_interval}")
            logger.debug(f"\tInterfaces of Interest: {service_config_interfaces_of_interest}")
            logger.debug(f"\tForce: {service_config_force}")
            logger.debug(f"\tIP Store File: {service_config_ip_store_file}")
    except FileNotFoundError:
        logger.error("The service_config.json file was not found.")
        raise Exception("The service_config.json file was not found. Please ensure it exists in the script's directory.")

    ip_store = IpStore(store_file=service_config_ip_store_file)
    if not ip_store.load():
        logger.info("No existing IP store found, initializing new store.")
        ip_store.hostname = socket.gethostname()
        ip_store.interfaces_of_interest = service_config_interfaces_of_interest
        ip_store.update_ips()
        ip_store.store()

    # If the interfaces of interest have changed, update them and send message immediately
    if ip_store.interfaces_of_interest != service_config_interfaces_of_interest:
        logger.info("Interfaces of interest have changed, updating and sending message immediately.")
    ip_store.interfaces_of_interest = service_config_interfaces_of_interest


    hostname = socket.gethostname()

    # Create the Slack messenger
    slack_messenger = SlackMessenger.SlackMessenger(device_name=hostname, secrets_file=args.secrets)

    ip_check_loop(slack_messenger, ip_store, service_config_check_interval, service_config_repost_interval, service_config_force or args.force)




if __name__ == "__main__":
    main()