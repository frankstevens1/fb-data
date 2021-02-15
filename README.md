# fb-data

## Setup

This guide covers setup on Windows 10 with WSL and on an EC2 instance on AWS. Choose the desired setup:

### [Local setup](##setup-on-wsl)

### [AWS EC2 setup](##setup-on-ec2)

---

## Usage

This section assumes you have succesfully completed setup on [WSL](##setup-on-wsl) or [EC2](##setup-on-ec2).

Before interacting with the script always change to the directory to which fb-data was copied & activate the python virtual environment:

```bash
cd /c/mnt/users/YOUR_WINDOWS_USERNAME/fb-data
source .venv/bin/activate
```

### Select games

Passing the `--games` argument prompts the user to select games to collect data for. If a cached list of games is available and up to date then the cached list will be used. If not, a list of games with live statistics available is scraped from the source and a cache is saved in the fb-data directory as `games_list.json`.

```bash
python3 main.py --games
```

![gif](https://drive.google.com/uc?export=view&id=189afFyaWbS0PJCu0uLX4u6-e1hU-YzFq)

### Select schedule

Two data collection schedules are available. The _'at 90+ minutes'_ schedule sends significantly less requests to the source's server and will still retrieve minute by minute game data. It is recommended to use this schedule if you do not need access to the data while game is live.

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

### Commit selection

After selecting the games, passing `--commit` will commit the selection. Once committed, data for past games will be retrieved immediately and upcoming games will be scheduled.

```bash
python3 main.py --commit
```

### View games selected

To view the games that have been selected for data collection pass `--check` to print out the current selection.

```bash
python3 main.py --check
```

![gif](https://drive.google.com/uc?export=view&id=1rGqww4dRgizU37OZMmDuuhR9W98vSQAL)

### Clear all

Pass `--clear` to clear selected games and remove all scheduled jobs from the cron table.

```bash
python3 main.py --clear
```

![gif](https://drive.google.com/uc?export=view&id=1GNr9Ufs4qWttCV6ErbowMtNRVcIojHc_)

### Cron table

Once a schedule has been committed, the jobs are written to the user's cron table. An additional job is scheduled to clear the cron table 3 hours after the last selected match's kick off time _(only clears cron jobs created by this app)_.

```bash
crontab -l
```

Check status or start/stop the system's cron service. **Cron should be active in order for scheduled jobs to run!**

```bash
sudo service cron status
sudo service cron start
sudo service cron stop
```

### Directories

Game data is saved in `./fb-data/games` directory.

Application logs are saved in the `./fb-data/logs` directory.

---

## Setup on WSL

### 1. WSL version

The fb-data application can be run locally from using WSL 1 with any Ubuntu distro. Unfortunately WSL 2 is not (yet) possible. You can change an active WSL 2 instance to version 1 by running (insert the appropirate distro name):

```powershell
wsl --set-version <Distro> 1
```

To get available Distro names, run:

```powershell
wsl -l -v
```

### 2. Python, project directory & virtual environment

- Ensure python3 is installed (on Ubuntu, this is installed out of the box). Verify by running:

```bash
python3 --version
```

- If Python 3.x.x was returned, we are good to go.
Now we can  install python pip and venv (package manager and virutal environment):

```bash
sudo apt -y install python-pip && sudo apt -y install python-venv
```

- Now we are ready to setup the project directory. Change to the directory where you wish to store the project. Within WSL we can access Windows file system, a recommended location would be (replace your windows username):

```bash
cd /mnt/c/Users/YOUR_WINDOWS_USERNAME
```

- You will be able to access all application files (such as game data collected) from the Windows file explorer. To copy the repository to the current directory, run:

```bash
git clone https://github.com/frankstevens1/fb-data.git
```

- The directory `fb-data` has been copied to the current directory with all project contents. Now we need to create a python virtual environment and install all dependencies:

```bash
cd fb-data
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Chrome and chromedriver

Although we are running the app from our WSL ubuntu vm, the driver and browser of choice will be activated within Windows. Therefore, the browser and driver should be installed on Windows and they should be of the same version.

This guide uses Chrome and chromedriver. If you choose to use the same setup as this guide then simply run the Google Chrome installer found in `./fb-data/chromedriver/ChromeSetup.exe` to install/update Google Chrome and then move on to next step.

Should you wish to use another browser, you will need to download the matching driver for that browser.

### 4. Configuration settings (local)

Some configuration settings need to be set in order to use fb-data. The project directory contains a json file with the urls of the data source and some additional user data. I will provide you with the correct values for "URL_1" & "URL_2"

- To edit `config_sample.json` in notepad run:

```bash
notepad.exe config.json
```

- `config_sample.json` is structured as follows, replace the values for "URL_1", "URL_2" & "USER_NAME" and save it as `config.json`.

```json
{
    "URL_1": "PASTE URL_1 THAT I PROVIDED HERE",
    "URL_2": "PASTE URL_2 THAT I PROVIDED HERE",
    "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36",
    "USER_NAME": "ubuntu",
    "LOCAL": 1
}
```

- "USER_AGENT" is correct for Google Chrome, if you choose to use another browser change this to the correct [user agent](https://user-agents.net/).

- "LOCAL": 1 when running locally or 0 when running on EC2.

- "USER_NAME": your username on WSL, run `whoami` in bash to return your username.

**You are now ready to [use](#usage) fb-data!**

---

## Setup on EC2

 An EC2 instance can be launched from an Amazon Machine Image (AMI). If you are ready to begin setup on EC2, let me know, then I'll give your account permission to use the AMI. There are costs involved with hosting an AMI, so I will take down the AMI after 24h, so launch an image from it within 24h from requesting.

 Once I've granted your AWS account permission to use the AMI you should find it in the navigation pane under Images > AMIs and then filter for Private AMIs.

### 1. Launch EC2 instance from AMI

Find the AMI shared with you & launch an instance from it. The setup wizard will ask for several settings, the defaults will suffice. The settings that need to be set to gain access to the instance via SSH are described below:

- Under tab '6. Configure Security Group', add the settings as shown in the screenshot below:

    1. Add an HTTP rule with _Custom_ source and `0.0.0.0/0, ::/0` value
    2. Add an HTTPS rule with _Custom_ source and `0.0.0.0/0, ::/0` value
    3. Add an SSH rule & change the source to _My IP_ and your IP Address will be populated as the value, this is the IP Address that will be granted SSH connection to your EC2 instance.

![step3](https://drive.google.com/uc?export=view&id=1IjcCsYo9YkOUIUR-MSjf33wfcQPGuMr_)

- Assign an existing keypair to the instance or create a new one. This keypair can be used to gain access to the EC2 instance via SSH. Save it in a safe place.

### 2. Setup SSH client

The client is your local machine. Use powershell (_run as administrator_) to perform the following checks.

- Check if OpenSSH.Client is installed:

```powershell
Get-WindowsCapability -Online | ? Name -like 'OpenSSH*'
```

- If not installed:

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
```

- Check if `sshd` is running:

```powershell
Get-Service sshd
```

- If not running:

```powershell
Start-Service sshd
```

- Set `sshd` to run at startup:

```powershell
Set-Service -Name sshd -StartupType 'Automatic'
```

### 3. Connect to EC2 instance

If necessary refer to [AWS documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AccessingInstances.html).

```powershell
ssh -i C:/path/to/mykeypair.pem ubuntu@my_instance_public_dns_name
```

Replace `C:/path/to/mykeypair.pem` with the path to key pair [created](###Create-kaypair).
Replace `my_instance_public_dns_name` with the Public IPv4 DNS found under instance summary in [AWS console](https://console.aws.amazon.com/).

### 4. Configuration settings (aws)

A config file is required to use fb-data, it is a json file that contains the urls of the data source and user data. The file is structured as follows and I will provide you with a link to download it with the appropriate URLs populated.

- config.json should be saved in fb-data directory.

```json
{
    "URL_1": "PASTE URL_1 THAT I PROVIDED HERE",
    "URL_2": "PASTE URL_2 THAT I PROVIDED HERE",
    "USER_AGENT": "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/87.0.4280.88 Chrome/87.0.4280.88 Safari/537.36",
    "USER_NAME": "ubuntu",
    "LOCAL": 0
}
```

- "USER_AGENT": is correct for Chromium, this is the browser used when running from EC2 instance.

- "LOCAL": 1 when running locally or 0 when running on EC2.

- "USER_NAME": your username on the EC2 instance, run `whoami` in bash to return your username. On EC2 it is usually ubuntu.
