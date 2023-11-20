# openvpn-access-bot
Manage your openvpn server via telegram-bot. Create/Revoke clients, watch server stats and more.

## Install
Install python3-full and python3-pip:
- ```sudo apt update```
- ```sudo apt install python3-full```
- ```sudo apt install python3-pip```

Prepare openvpn server first, get the script and make it executable:

```bash
curl -O https://raw.githubusercontent.com/angristan/openvpn-install/master/openvpn-install.sh
chmod +x openvpn-install.sh
```

Then run it:

```sh
./openvpn-install.sh
```

You need to run the script as root and have the TUN module enabled.

The first time you run it, you'll have to follow the assistant and answer a few questions to setup your VPN server.

Clone repo and install dependencies:
- `git clone https://github.com/imhassla/openvpn-access-bot.git`
- `cd openvpn-access-bot`
- `python3 -m venv env`
- `source env/bin/activate`
- `pip install -r requirements.txt`
  
