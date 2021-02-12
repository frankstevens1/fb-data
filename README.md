# fb-data

## Usage

First, change to the project directory and activate python virtual environment:

```bash
cd /home/fb-data
source .venv/bin/activate
```

### Select games

Games need to be selected in order to stage them for data collection. Passing the --games argument prompts the user to select games to collect data for. The list of games with live statistics available is scraped from the source. A cache of the games list is saved in the project folder: `games_list.json`. If the cached list is outdated or not available then games will be scraped otherwise the cached list is used.

```bash
python3 main.py --games
```

![gif](https://drive.google.com/uc?export=view&id=189afFyaWbS0PJCu0uLX4u6-e1hU-YzFq)

### Select schedule

Two data collection schedules are available. The 'at 90+ minutes' schedule sends significantly less requests to the source's server and will still collect minute by minute game data. It is recommended to use this schedule if you do not need access to live data. Functionality for alternative schedules could be added upon request.

#### Data refresh schedules

|time            |at 90+ minutes |every 15 minutes|
|---                     |---: |---:|
|kick-off (ko)           |✘   |✘|
|ko +  15 min            |✘   |✓|
|ko +  30 min            |✘   |✓|
|ko +  45 min (HT)       |✘   |✓|
|ko +  60 min (start 2nd)|✘   |✓|
|ko +  75 min            |✘   |✓|
|ko +  90 min            |✘   |✓|
|ko + 105 min (FT)       |✓   |✓|
|ko + 120 min (ST)       |✓   |✓|
|ko + 135 min (ET)       |✓   |✓|
|ko + 150 min (ET)       |✓   |✓|
|ko + 150 min (FT)       |✓   |✓|
|ko + 165 min (ST)       |✓   |✓|
|ko + 180 min            |✓   |✓|

### View games selected

To view the games that have been selected for data collection pass the `--check` argument to print out the current selection.

```bash
python3 main.py --check
```

![gif](https://drive.google.com/uc?export=view&id=1rGqww4dRgizU37OZMmDuuhR9W98vSQAL)

### Commit selection

After deciding on the games to collect dat for, the `--commit` argument can be passed to commit the selection. Data for past games will be scraped immediately and upcoming games will be scheduled. The schedule is decided by the user.

```bash
python3 main.py --commit
```

### Clear all

Pass `--clear` to clear selected games and remove all scheduled jobs from the cron table.

```bash
python3 main.py --clear
```

![gif](https://drive.google.com/uc?export=view&id=1GNr9Ufs4qWttCV6ErbowMtNRVcIojHc_)

### Cron table

Once a schedule has been committed the jobs are written to the user's cron table. An additional job is scheduled to clear the cron table 3 hours after the last match's kick off time _(only clears jobs created by this app)_.

```bash
crontab -l
```

Check status or start/stop the system's cron service. Cron should be active in order for scheduled jobs to run.

```bash
sudo service cron status
sudo service cron start
sudo service cron stop
```

### Directories

Game data is saved in games directory:

```bash
cd /home/fb-data/games
```

Application logs are saved in the logs directory:

```bash
cd /home/fb-data/logs
```

## Setup on on EC2 instance from Amazon Machine Image (AMI)

Follow the steps described in this [article](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/get-set-up-for-amazon-ec2.html#create-a-key-pair) to create a keypair.

### SSH Connection

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
