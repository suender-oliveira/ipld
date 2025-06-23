#!/usr/bin/env bash
# Licensed Materials - Property of IBM
#
# (C) COPYRIGHT International Business Machines Corp. 2022
# All Rights Reserved
#
# US Government Users Restricted Rights - Use, duplication or
# disclosure restricted by GSA ADP Schedule Contract with IBM Corp.
####################################################################################
    echo "************************************************************************************************"
    echo "************************************************************************************************"
    echo "************************************************************************************************"
    echo "###########  ############      ########      ########"
    echo "###########  ###############   #########    #########"
    echo "   #####        ####   #####     ########  ########           AUTOMATED LOG ANALYSIS FOR z/OS"
    echo "   #####        ###########      ####  ### ### ####           "
    echo "   #####        ###########      ####  ####### ####"
    echo "   #####        ####   #####     ####   #####  ####           VERSION: 1.0"
    echo "###########  ###############   ######    ###   ######"
    echo "###########  ############      ######     #    ######"
    echo "************************************************************************************************"
    echo "************************************************************************************************"
    echo "************************************************************************************************"
    echo ""
printf "Automated tasks was started for the IPL analysis \t............................... [\e[3;4;33m WAIT \e[0m]\n"
printf "┬\n"

spin()
{
  spinner="/|\\-/|\\-"
  while :
  do
    for i in `seq 0 7`
    do
      echo -n "${spinner:$i:1}"
      echo -en "\010"
      sleep 0.2
    done
  done
}

####################################################################################
# Looping the lpar config base
for list_lpar in `cat lparesdb.sh | grep -v "#"`
do
    lpar_host=$(echo $list_lpar | cut -d"|" -f1)
    lpar_hostname=$(echo $lpar_host | cut -d"." -f1)
    qualifier=$(echo $list_lpar | cut -d"|" -f2)
    userid=$(echo $list_lpar | cut -d"|" -f3)
    lpares_array[i=$((i+1))]=$lpar_hostname

    checking_ipl_space=$(ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=error $userid@$lpar_host \
    "if [[ -d /tmp/ipl_analysis/$lpar_hostname ]];then;rm -rf /tmp/ipl_analysis/$lpar_hostname && mkdir -p /tmp/ipl_analysis/$lpar_hostname;else;mkdir -p /tmp/ipl_analysis/$lpar_hostname ;fi" \
    ) > /dev/null 2>&1

    if [ -f "methods_$lpar_hostname.sh" ]
    then
        scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=error ipld_* patterns main.sh "methods_$lpar_hostname.sh" \
        $userid@$lpar_host:/tmp/ipl_analysis/$lpar_hostname/  > /dev/null 2>&1
    else
        scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=error ipld_* patterns main.sh methods.sh \
        $userid@$lpar_host:/tmp/ipl_analysis/$lpar_hostname/  > /dev/null 2>&1
    fi

        ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=error $userid@$lpar_host \
            "/tmp/ipl_analysis/$lpar_hostname/main.sh -r cli -a $lpar_host -q $qualifier -o JSON" &
done

while [ `echo ${#lpares_array[@]}` != `echo ${#lpares_status_array[@]}` ]
do
    tput ed
    [[ -n ${lpares_status_array[@]} ]] && unset lpares_status_array
    for test_lpar in "${lpares_array[@]}"
    do
        checking_lpar_exec=$(ps -ef | grep $test_lpar | grep -v grep | awk '{print $2}' | wc -l)
        upperized_test_lpar=$(echo $test_lpar | tr '[:lower:]' '[:upper:]')
        if [ $checking_lpar_exec -gt 0 ]
        then
            printf "├ $upperized_test_lpar \t....................................................................... [\e[3;4;33m WAIT \e[0m]\n"
        else
            printf "├ $upperized_test_lpar \t....................................................................... [\e[3;4;32m DONE \e[0m]\n"
            lpares_status_array[j=$((j+1))]=$test_lpar
        fi
    done
    sleep 2
    tput cuu $(echo ${#lpares_array[@]})
done
tput cud $(echo "${#lpares_array[@]}+1" | bc -l)

spin &
SPIN_PID=$!
printf "Downloading results "
for list_lpar in `cat lparesdb.sh | grep -v "#"`
do
    lpar_host=$(echo $list_lpar | cut -d"|" -f1)
    lpar_hostname=$(echo $lpar_host | cut -d"." -f1)

    if [[ -d "results/$lpar_hostname" ]]
    then
        rm -rf "results/$lpar_hostname"
        mkdir "results/$lpar_hostname"
        $(scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=error $userid@$lpar_host:/tmp/ipl_analysis/$lpar_hostname/*.CSV ./"results/$lpar_hostname")  > /dev/null 2>&1
    else
        mkdir "results/$lpar_hostname"
        $(scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=error $userid@$lpar_host:/tmp/ipl_analysis/$lpar_hostname/*.CSV ./"results/$lpar_hostname")  > /dev/null 2>&1
    fi
done
printf "\nCleaning  "
cleaning_ipl_space=$(ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=error $userid@$lpar_host \
    "rm -rf /tmp/ipl_analysis/$lpar_hostname && rm -rf /tmp/ipl_analysis" \
    ) > /dev/null 2>&1

printf "\t....................................................................... [\e[3;4;32m DONE \e[0m]\n\n"
kill -9 $SPIN_PID > /dev/null 2>&1

printf "Automated tasks was ended for the IPL analysis \t....................................... [\e[3;4;32m DONE \e[0m]\n\n" > /dev/null 2>&1
echo "Done."