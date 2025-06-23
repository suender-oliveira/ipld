import os
import socket
import requests
import base64
from dotenv import load_dotenv
from remote_async_ssh import RemoteSSHConnection

load_dotenv()


class DryRun:
    def __init__(self, lpar, username, syslog_qualifier):
        self.lpar = lpar
        self.username = username
        self.syslog_qualifier = syslog_qualifier

    async def check_ssh_connection(self):
        remote_ssh_checks = []

        ssh_client = RemoteSSHConnection(self.lpar, self.username)

        try:
            check_ssh_login = await ssh_client.run_command("cd $HOME; pwd 2>&1")
            remote_ssh_checks.append(
                {"check_ssh_login": check_ssh_login.split("/")[-1]}
            )

            check_dataset_access = await ssh_client.run_command(
                (
                    (
                        (
                            f'check=$(tsocmd "listcat level({self.syslog_qualifier})" | grep NONVSAM'
                            + ' | egrep "LOG|BLDR01" | tail -2 |'
                            + " head -1 |"
                            + ' cut -d" " -f3)'
                        )
                        + " && "
                    )
                    + "head -1000 \"//'$check'\" | wc -l 2>&1"
                )
            )
            remote_ssh_checks.append(
                {"check_dataset_access": check_dataset_access}
            )

            check_tmp_space = await ssh_client.run_command(
                "df -kP /tmp | tail -1 | awk '{print $5}'"
            )
            remote_ssh_checks.append(
                {"check_tmp_space": check_tmp_space.replace("%", "")}
            )
            remote_ssh_checks.append({"check_tmp_space": 20})

        except Exception as error:
            remote_ssh_checks.append({"check_ssh_login": str(error)})

    async def check_egress_firewall(self):
        lpar_ip_address = socket.gethostbyname(self.lpar)
        project_id = os.getenv("PROJECT_ID")
        cluster_id = os.getenv("CLUSTER_ID")
        user_key = os.getenv("CIRRUS_USER")
        pass_key = os.getenv("CIRRUS_PASSWORD")
        api_key_str = f"{user_key}:{pass_key}"
        x_api_key = base64.b64encode(api_key_str.encode("utf-8")).decode(
            "utf-8"
        )
        token_url = "https://api.cirrus.ibm.com/v1/identity/token"
        egress_rules_url = f"https://api.cirrus.ibm.com/v1/firewall/flows/{project_id}/{cluster_id}"

        headers = {"x-api-key": x_api_key}
        response = requests.post(token_url, headers=headers, timeout=10)
        data = response.json()

        headers = {"Authorization": f'Bearer {data["access_token"]}'}
        response = requests.get(egress_rules_url, headers=headers, timeout=10)
        data = response.json()

        for egress in data["egress"]:
            if egress["destination_ip"] == lpar_ip_address:
                return 1

        return 0
