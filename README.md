# openvpn-access-bot
Manage your openvpn server via telegram-bot. Create/Revoke clients, watch server stats and more.

## Install
python3-full and python3-pip required:
```bash
sudo apt update && sudo apt install git screen python3-full python3-pip -y
```

prepare openvpn server first, get the script, make it executable and run as sudo:
```bash
curl -O https://raw.githubusercontent.com/angristan/openvpn-install/master/openvpn-install.sh && chmod +x openvpn-install.sh && sudo bash openvpn-install.sh
```

You need to run the script as root and have the TUN module enabled, you'll have to follow the assistant and answer a few questions to setup your VPN server.

Clone repo and install dependencies:
```bash
git clone https://github.com/imhassla/openvpn-access-bot.git
cd openvpn-access-bot
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

Replace 'TOKEN' and 'admin_ids' in openvpn-access-bot.py script with your data and run it after:
```bash
screen python3 openvpn-access-bot.py
```
  
Functions:

![alt text](https://github.com/imhassla/openvpn-access-bot/blob/main/img/demo0.png)

![alt text](https://github.com/imhassla/openvpn-access-bot/blob/main/img/demo1.png)

![alt text](https://github.com/imhassla/openvpn-access-bot/blob/main/img/demo2.png)

![alt text](https://github.com/imhassla/openvpn-access-bot/blob/main/img/demo3.png)

![alt text](https://github.com/imhassla/openvpn-access-bot/blob/main/img/demo4.png)
