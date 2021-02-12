# fb-data

## Setup on on EC2 instance from Amazon Machine Image (AMI)

### Create keypair

Follow the steps described in this [article](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/get-set-up-for-amazon-ec2.html#create-a-key-pair) to create a keypair.

## SSH Connection

### Setup client

The client is your local machine. Use powershell (_run as administrator_) to perform the following checks.

* Check if OpenSSH.Client is installed:

```powershell
Get-WindowsCapability -Online | ? Name -like 'OpenSSH*'
```

* If not installed:

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
```

* Check if `sshd` is running:

```powershell
Get-Service sshd
```

* If not running:

```powershell
Start-Service sshd
```

* Set `sshd` to run at startup:

```powershell
Set-Service -Name sshd -StartupType 'Automatic'
```

### Connect to EC2 instance

If necessary refer to [AWS documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AccessingInstances.html).

```powershell
ssh -i C:/path/to/mykeypair.pem ubuntu@my_instance_public_dns_name
```

Replace `C:/path/to/mykeypair.pem` with the path to key pair [created](###Create-kaypair).
Replace `my_instance_public_dns_name` with the Public IPv4 DNS found under instance summary in [AWS console](https://console.aws.amazon.com/).

## Usage

Project directory

```bash
cd /home/fb-data
```

### Select games

Games need to be selected in order to stage them for data collection.

```bash
python3 main.py --games
```

### Commit selection to schedule

After making a selection of games, past games will be fetched immediately and cron jobs for upcoming games will be written to the cron table.

```bash
python3 main.py --commit
```

### Manage schedule & selection

Check games scheduled/selected

```bash
python3 main.py --check
```

Clear all games scheduled/selected

```bash
python3 main.py --clear
```

### Cron table

List all cron jobs

```bash
crontab -l
```

Check status or start/stop cron

```bash
sudo service cron status
sudo service cron start
sudo service cron stop
```

Manually edit cron table

```bash
crontab -e
```

### Directories

Game data is saved in games directory

```bash
cd /home/fb-data/games
```

Application logs are saved in the logs directory

```bash
cd /home/fb-data/logs
```

## Userdata for AMI launch template

```bash
#!/bin/bash
apt update
apt upgrade -y
apt install -y python3-pip
apt-get install -y python3-venv
apt-get install -y unzip openjdk-8-jre-headless xvfb libxi6 libgconf-2-4 xdg-utils xserver-xephyr tigervnc-standalone-server xfonts-base
apt install -y chromium-browser
apt install -y chromium-chromedriver
chown root:root /usr/bin/chromedriver
chmod 0755 /usr/bin/chromedriver
chmod a+rwx /home
cd /home
git clone https://github.com/frankstevens1/fb-data.git
chmod a+rwx /home/fb-data
cd fb-data
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
# FILELINK
# FILENAME
wget $FILELINK -O $FILENAME
```
