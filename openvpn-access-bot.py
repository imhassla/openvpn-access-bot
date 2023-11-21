import telebot
import os
import time
import psutil
import subprocess
import shutil
import re
import tempfile
import subprocess
import glob
from datetime import datetime
from telebot import types
import dotenv

dotenv.load_dotenv()
TOKEN = os.getenv('TOKEN')
ADMIN_IDS = os.getenv('ADMIN_IDS')
 
bot = telebot.TeleBot(TOKEN)
script_dir = os.path.dirname(os.path.abspath(__file__))

def open_as_sudo(path):
    return os.popen(f'sudo cat {path}', 'r')

def vpn_log():
    with open_as_sudo('/var/log/openvpn/status.log') as f:
        lines = f.readlines()
    lines = lines[:lines.index('GLOBAL STATS\n')]
    return ''.join(lines)

def restart_vpn():
    os.system('sudo systemctl restart openvpn@server')

def admin_required(func):
    def wrapper(message):
        if str(message.chat.id) not in ADMIN_IDS:
            bot.reply_to(message, "You do not have permission to execute this command.")
            return
        return func(message)
    return wrapper

def c2c_status():
    
    with open_as_sudo('/etc/openvpn/server.conf') as file:
        lines = file.readlines()

    if 'client-to-client\n' not in lines:
        return 'disabled'
    elif 'client-to-client\n' in lines:
        return 'enabled'

def manage_client_to_client(switch):
    assert switch in ['enable', 'disable'], "Invalid argument. Only 'enable' or 'disable' are allowed."

    with open('/etc/openvpn/server.conf', 'r') as file:
        lines = file.readlines()

    if switch == 'enable':
        os.system('sudo iptables -D FORWARD -i tun0 -o tun0 -j DROP')
        os.system('sudo iptables -D INPUT -i tun0 -j DROP')
        os.system('sudo iptables -D OUTPUT -o tun0 -j DROP')
        os.system('sudo iptables -D INPUT -i tun0 -s 10.8.0.1 -j ACCEPT')
        os.system('sudo iptables -D OUTPUT -o tun0 -d 10.8.0.1 -j ACCEPT')
        os.system('sudo iptables -P INPUT ACCEPT')
        os.system('sudo iptables -P FORWARD ACCEPT')
        os.system('sudo iptables -P OUTPUT ACCEPT')
        lines.append('client-to-client\n')
    elif switch == 'disable':
        os.system('sudo iptables -A FORWARD -i tun0 -o tun0 -j DROP')
        os.system('sudo iptables -A INPUT -i tun0 -j DROP')
        os.system('sudo iptables -A OUTPUT -o tun0 -j DROP')
        os.system('sudo iptables -A INPUT -i tun0 -s 10.8.0.1 -j ACCEPT')
        os.system('sudo iptables -A OUTPUT -o tun0 -d 10.8.0.1 -j ACCEPT')
        lines.remove('client-to-client\n')

    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
        for line in lines:
            temp.write(line)
        temp_path = temp.name

    os.system(f'sudo mv {temp_path} /etc/openvpn/server.conf')
    time.sleep(1)
    #os.system('sudo systemctl restart openvpn@server')


def get_server_ip():
    command = "cat /etc/openvpn/client-template.txt | grep -E 'remote ' | awk '{printf $2 \":\" $3 \"\\n\"}'"
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    output, error = process.communicate()
    if error:
        print(f"An error occurred: {error}")
    else:
        return output.decode('utf-8').strip()
    
def newClient(name):
    CLIENT = name
    PASS = '1'
    with open_as_sudo('/etc/openvpn/easy-rsa/pki/index.txt') as f:
        CLIENTEXISTS = f.read().count(f"/CN={CLIENT}\n")

    if CLIENTEXISTS == 1:
        print("The specified client CN was already found in easy-rsa, please choose another name.")
        return
    else:
        os.chdir('/etc/openvpn/easy-rsa/')
        if PASS == '1':
            subprocess.run(['sudo', './easyrsa', '--batch', 'build-client-full', CLIENT, 'nopass'])
        print(f"Client {CLIENT} added.")

    if os.system('sudo grep -qs "^tls-crypt" /etc/openvpn/server.conf') == 0:
        TLS_SIG = "1"
    elif os.system('sudo grep -qs "^tls-auth" /etc/openvpn/server.conf') == 0:
        TLS_SIG = "2"

    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
        temp.write(open_as_sudo("/etc/openvpn/client-template.txt").read())
        temp.write("<ca>\n")
        temp.write(open_as_sudo("/etc/openvpn/easy-rsa/pki/ca.crt").read())
        temp.write("</ca>\n")
        temp.write("<cert>\n")
        temp.write(open_as_sudo(f"/etc/openvpn/easy-rsa/pki/issued/{CLIENT}.crt").read())
        temp.write("</cert>\n")
        temp.write("<key>\n")
        temp.write(open_as_sudo(f"/etc/openvpn/easy-rsa/pki/private/{CLIENT}.key").read())
        temp.write("</key>\n")

        if TLS_SIG == "1":
            temp.write("<tls-crypt>\n")
            temp.write(open_as_sudo("/etc/openvpn/tls-crypt.key").read())
            temp.write("</tls-crypt>\n")
        elif TLS_SIG == "2":
            temp.write("key-direction 1\n")
            temp.write("<tls-auth>\n")
            temp.write(open_as_sudo("/etc/openvpn/tls-auth.key").read())
            temp.write("</tls-auth>\n")

    os.system(f'sudo mv {temp.name} {os.path.join(script_dir, f"{CLIENT}.ovpn")}')

    print(f"The configuration file has been written to {script_dir}/{CLIENT}.ovpn.")
    print("Download the .ovpn file and import it in your OpenVPN client.")

def revoke_client(name):
    # Check if the user exists
    if not os.path.isfile(f'{name}.ovpn'):
        return "User does not exist."
    # Navigate to the required directory
    os.chdir('/etc/openvpn/easy-rsa/')
    # Check if the user exists in PKI
    with open_as_sudo('/etc/openvpn/easy-rsa/pki/index.txt') as f:
        if f"V.*CN={name}" not in f.read():
            print("A client with this name does not exist.")
    # Revoke the user's certificate
    subprocess.call(f'sudo ./easyrsa --batch revoke {name}', shell=True)
    # Generate a new CRL
    subprocess.call('sudo EASYRSA_CRL_DAYS=3650 ./easyrsa gen-crl', shell=True)
    # Update the CRL
    # Copy the file with superuser rights
    subprocess.call('sudo cp /etc/openvpn/easy-rsa/pki/crl.pem /etc/openvpn/crl.pem', shell=True)
    # Change the permissions on the file with superuser rights
    subprocess.call('sudo chmod 644 /etc/openvpn/crl.pem', shell=True)
    # Delete the user's files
    for root, dirs, files in os.walk('/home/'):
        for file in files:
            if file == f"{name}.ovpn":
                subprocess.call(f'sudo rm {os.path.join(root, file)}', shell=True)
    if os.path.isfile(f"/root/{name}.ovpn"):
        subprocess.call(f'sudo rm /root/{name}.ovpn', shell=True)
    # Update the ipp.txt file
    with open_as_sudo('/etc/openvpn/ipp.txt') as f:
        lines = f.readlines()
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
        for line in lines:
            if line.strip("\n") != f"{name}":
                temp.write(line)
    # Move the temporary file to the target file with superuser rights
    os.system(f'sudo mv {temp.name} {"/etc/openvpn/ipp.txt"}')
    # Update the index.txt file
    subprocess.call('sudo cp /etc/openvpn/easy-rsa/pki/index.txt /etc/openvpn/easy-rsa/pki/index.txt.bk', shell=True)
    return "Certificate for client revoked."

commands = [
    types.BotCommand('new', 'create vpn key'),
    types.BotCommand('revoke', 'delete user from serer'),
    types.BotCommand('c2c', 'enable/disable client-to-client traffic'),
    types.BotCommand('restart', 'restart vpn server'),
    types.BotCommand('info', 'check server status'),
]
bot.set_my_commands(commands)

@bot.message_handler(commands=['start'])
#@admin_required
def start(message):
    bot.send_message(message.chat.id, "Welcone to openvpn-access-bot!\nYou can see a list of available commands in the menu")

@bot.message_handler(commands=['new'])
@admin_required
def new_user(message):
    os.chdir(script_dir)
    msg = bot.reply_to(message, "Enter new user name in format [a-zA-Z0-9]:")
    bot.register_next_step_handler(msg, create_new_user)

def create_new_user(message):
    date_prefix = datetime.now().strftime('%H_%M_%d_%m_%Y')
    if not re.match("^[a-zA-Z0-9]*$", message.text):
        bot.reply_to(message, "Invalid input format. Enter the command again and enter the name in the required format.")
        return
    name = message.text + '_' + date_prefix
    if os.path.isfile(f'{name}.ovpn'):
        bot.reply_to(message, "The user already exists. Here is the key-file:")
        bot.send_document(message.chat.id, open(f'{name}.ovpn', 'rb'))
    else:
        newClient(name)
        os.chdir(script_dir)
        bot.reply_to(message, 'The user has been created. Here is the key-file:')
        bot.send_document(message.chat.id, open(f'{name}.ovpn', 'rb'))

@bot.message_handler(commands=['revoke'])
@admin_required
def revoke_user(message):
    os.chdir(script_dir)
    users = [os.path.splitext(os.path.basename(file))[0] for file in glob.glob('*.ovpn')]
    bot.reply_to(message, "Users list:\n" + '\n'.join(users))
    msg = bot.reply_to(message, "Enter username to revoke:")
    bot.register_next_step_handler(msg, revoke_process)

def revoke_process(message):
    if message.text.startswith('/'):
        bot.reply_to(message, "Invalid input format. Enter the command again and enter the name in the required format.")
        return
    name = message.text
    if not os.path.isfile(f'{name}.ovpn'):
        bot.reply_to(message, "User does not exist.")
    else:
        revoke_client(name)
        bot.reply_to(message, "User deleted.")

@bot.message_handler(commands=['c2c'])
@admin_required
def c2c_traffic(message):
    status = c2c_status()
    markup = types.InlineKeyboardMarkup()
    itembtn1 = types.InlineKeyboardButton('Enable' if status == 'disabled' else 'Disable', callback_data='change_c2c_status')
    markup.add(itembtn1)

    bot.send_message(message.chat.id, f"Current Client-to-Client status: {status}. Do you want to change it?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'change_c2c_status')
def change_c2c_status(call):
    current_status = c2c_status()
    new_status = 'enable' if current_status == 'disabled' else 'disable'
    manage_client_to_client(new_status)
    bot.answer_callback_query(call.id, f"c2c status changed to: {new_status}")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(commands=['restart'])
@admin_required
def restart_server(message):
    markup = types.InlineKeyboardMarkup()
    itembtn1 = types.InlineKeyboardButton('Restart vpn server', callback_data='restart')
    markup.add(itembtn1)
    bot.send_message(message.chat.id, f"really??", reply_markup=markup)
@bot.callback_query_handler(func=lambda call: call.data == 'restart')
def restart(call):
    bot.answer_callback_query(call.id, f"restarted!")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    restart_vpn()


@bot.message_handler(commands=['info'])
@admin_required
def server_stat(message):
    os.chdir(script_dir)
    # Getting CPU information
    cpu_usage = psutil.cpu_percent(interval=1)
    # Getting RAM information
    memory_info = psutil.virtual_memory()
    total_memory = memory_info.total / (1024.0 ** 2)
    used_memory = memory_info.used / (1024.0 ** 2)
    memory_percent = memory_info.percent

    # Getting disk information
    disk_info = psutil.disk_usage('/')
    total_disk = disk_info.total / (1024.0 ** 3)
    used_disk = disk_info.used / (1024.0 ** 3)
    disk_percent = disk_info.percent

    # Getting OpenVPN status
    try:
        vpn_status = subprocess.check_output(['systemctl', 'is-active', 'openvpn@server'])
        vpn_status = 'active'
    except subprocess.CalledProcessError:
        vpn_status = 'inactive'

    # Getting system I/O statistics
    net_io_counters = psutil.net_io_counters()

    # Converting bytes to megabytes
    bytes_sent_mb = net_io_counters.bytes_sent / (1024 * 1024)
    bytes_recv_mb = net_io_counters.bytes_recv / (1024 * 1024)

    vpn_clients = vpn_log()
    server_ip = get_server_ip()
    traffic_c2c = c2c_status()

    # Sending information to the user
    bot.reply_to(message, f"CPU load: {cpu_usage}%\n"
                          f"RAM used: {used_memory:.1f}MB of {total_memory:.1f}MB ({memory_percent}%)\n"
                          f"Disk space used: {used_disk:.1f}GB of {total_disk:.1f}GB ({disk_percent}%)\n"
                          f"OpenVPN status: {vpn_status} {server_ip}\n\n{vpn_clients}\n"
                          f"Client_2_Client: {traffic_c2c}\n\n"
                          f"System network I/O statistics:\n"
                          f"Sent: {bytes_sent_mb:.1f}MB\n"
                          f"Received: {bytes_recv_mb:.1f}MB"
                          )

while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print('Connection error, reconnect after 15 seconds...')
        time.sleep(15)
