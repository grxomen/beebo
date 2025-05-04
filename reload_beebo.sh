#!/bin/bash

cd /root/beebo || exit 1
git pull origin main || exit 1

# Wait 3 seconds to let Beebo send the Discord response
sleep 3

sudo systemctl restart beebo || exit 1

