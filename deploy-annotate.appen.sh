#!/bin/bash
ibmcloud target -r us-east
ibmcloud target -g "JKs Resource Group"
ibmcloud fn namespace target Kellerman-Functions

./build-image.sh

ibmcloud fn action update utils/appen --docker kineticsquid/appen:latest annotate.appen.py --web true -p USERID ${USERID} -p PASSWORD ${PASSWORD}

# Now list the package
ibmcloud fn package get utils
# Get the definition of the function
ibmcloud fn action get utils/appen
# invoke the function
ibmcloud fn action invoke utils/appen --blocking -p action Test
# See the log results
echo "Make sure the activation reported by the next command is the most recent one executed. Look for activation id"
ibmcloud fn activation get -l

echo "URL is https://us-east.functions.appdomain.cloud/api/v1/web/634e7a7f-9928-4744-8190-f4bf5d671142/utils/appen"
