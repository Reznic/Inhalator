#!/bin/bash

VERSION=$(basename /mnt/dok/inhalator*.tar.gz | cut -d"." -f 1)

if [[ -d /home/pi/$VERSION ]]; then
	echo "Inhalator version is already $VERSION"
	sleep 3
	exit 0
fi

echo -n "Copying new files.."
sudo rm -rf /tmp/Inhalator
sudo tar xf /mnt/dok/inhalator*.tar.gz -C /tmp
sudo mv /tmp/Inhalator /home/pi/$VERSION

# In order to make the upgrade an atomic action..
# We copy the new version files and then change the service file to point it.
echo -n "Replacing inhalator service..."
sudo bash -c "sed -i 's/Inhalator/${VERSION}/' /usr/lib/systemd/user/inhalator.service"
echo -n "Sync files to flush..."
sudo sync

echo -n "Copying config.json file..."
sudo cp /home/pi/Inhalator/config.json /home/pi/$VERSION/config.json

echo -n "Running setup script... "
sudo /home/pi/${VERSION}/rasp_init/setup.sh 1> /dev/null
echo "Done."

echo -n "Deleting old version files... "
sudo rm -rf $(readlink /home/pi/Inhalator) 1> /dev/null
sudo rm -rf /home/pi/Inhalator 1> /dev/null
echo "Done."

echo -n "Stopping Inhalator service... "
sudo systemctl stop inhalator.service 1> /dev/null
echo "Done."

echo -n "Linking new version..."
sudo ln -s /home/pi/$VERSION /home/pi/Inhalator

echo -n "Reseting inhalator service..."
sudo bash -c "sed -i 's/${VERSION}/Inhalator/' /usr/lib/systemd/user/inhalator.service"

echo -n "Reloading inhalator service..."
sudo systemctl daemon-reload inhalator.service

echo -n "Sync files to flush.."
sudo sync

echo -n "Restarting service... "
sudo systemctl start inhalator.service 1> /dev/null
echo "Done."
sleep 2
