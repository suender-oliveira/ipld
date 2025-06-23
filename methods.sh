#!/bin/env sh
# Licensed Materials - Property of IBM
#
# (C) COPYRIGHT International Business Machines Corp. 2022
# All Rights Reserved
#
# US Government Users Restricted Rights - Use, duplication or
# disclosure restricted by GSA ADP Schedule Contract with IBM Corp.
####################################################################################

header(){
    ####################################################################################
    # Defining constant system name
    system_name=$(/bin/sysvar SYSNAME)

    clear
    echo "**************************************************************************************************************"
    echo "**************************************************************************************************************"
    echo "**************************************************************************************************************"
    echo "###########  ############      ########      ########"
    echo "###########  ###############   #########    #########"
    echo "   #####        ####   #####     ########  ########           AUTOMATED LOG ANALYSIS FOR z/OS"
    echo "   #####        ###########      ####  ### ### ####           IPL PROCESS ANALYSIS FOR $system_name"
    echo "   #####        ###########      ####  ####### ####"
    echo "   #####        ####   #####     ####   #####  ####           VERSION: 1.0"
    echo "###########  ###############   ######    ###   ######"
    echo "###########  ############      ######     #    ######"
    echo "**************************************************************************************************************"
    echo "**************************************************************************************************************"
    echo "**************************************************************************************************************"
    echo ""

    
}

defining_patterns(){
    ####################################################################################
    # Looping the registered patterns

    for i in `cat patterns`
    do
        increment_patterns=$increment_patterns"|"$i
    done
    patterns=$(echo $increment_patterns | sed 's/^.//')
}

ipl_processor(){
    nl $searchable_name_file | egrep $patterns | awk -v system_name="$system_name" -v original_name_file="$1" -f ipld_parsing.awk
}

date_to_epoch(){
    [ -z $1 ] && exit

    year=$(echo $1 | awk -F '-|:|_' '{print $1}' )
    month=$(echo $1 | awk -F '-|:|_' '{print $2}' )
    day=$(echo $1 | awk -F '-|:|_' '{print $3}' )
    hour=$(echo $1 | awk -F '-|:|_' '{print $4}' )
    minute=$(echo $1 | awk -F '-|:|_' '{print $5}' )
    second=$(echo $1 | awk -F '-|:|_' '{print $6}' )

    year_to_second=$(echo "($year - 1970) * 31557600" | bc -l)
    month_to_second=$(echo "$month * 2629800" | bc -l)
    day_to_seconds=$(echo "$day * 86400" | bc -l)
    hour_to_seconds=$(echo "$hour * 3600" | bc -l)
    minute_to_seconds=$(echo "$minute * 60" | bc -l)

    timestamp_unix=$(echo "$year_to_second+$month_to_second+$day_to_seconds+$hour_to_seconds+$minute_to_seconds+$second" | bc -l)

    echo "$timestamp_unix"
}

leading_zero_fill ()
{
    ####################################################################################
    # print the number as a string with a given number of leading zeros
    printf "%0$1d\\n" "$2"
}

calc_time(){

    start_timestamp=$(date_to_epoch $1)
    end_timestamp=$(date_to_epoch $2)

    diff_start_to_end=$(echo "$end_timestamp-$start_timestamp" | bc -l)

    if [ $diff_start_to_end -ge 86400 ]
    then
        while [ `expr "$diff_start_to_end/86400"` -ge 1 ]
        do
            diff_start_to_end=$((diff_start_to_end-86400))
            spent_days=$((spent_days+1))
        done
        
        # Second to Hour
        while [ `expr "$diff_start_to_end/3600"` -ge 1 ]
        do
            diff_start_to_end=$((diff_start_to_end-3600))
            spent_hour=$((spent_hour+1))
        done

        if [ -n $spent_hour]
        then
            spent_hour=$((spent_hour))
        else 
            spent_hour=0
        fi
        
        # Remaining Second to Minute
        while [ `expr "$diff_start_to_end/60"` -ge 1 ]
        do
            diff_start_to_end=$((diff_start_to_end-60))
            spent_minute=$((spent_minute+1))
        done

        echo "[ $spent_days day(s), $spent_hour hour(s), $spent_minute minute(s), $diff_start_to_end second(s) ]"

    else
        # Second to Hour
        while [ `expr "$diff_start_to_end/3600"` -ge 1 ]
        do
            diff_start_to_end=$((diff_start_to_end-3600))
            spent_hour=$((spent_hour+1))
        done
        if [ -n $spent_hour ]
        then
            spent_hour=$((spent_hour))
        else 
            spent_hour=0
        fi
        
        # Remaining Second to Minute
        while [ `expr "$diff_start_to_end/60"` -ge 1 ]
        do
            diff_start_to_end=$((diff_start_to_end-60))
            spent_minute=$((spent_minute+1))
        done

        echo "[ 0 day(s), $spent_hour hour(s), $spent_minute minute(s), $diff_start_to_end second(s) ]"

    fi
}

calc_time_cli(){

    [ -z $1 -o -z $2 ] && exit

    start_timestamp=$(date_to_epoch `echo $1 | sed 's/ /_/'`)
    end_timestamp=$(date_to_epoch `echo $2 | sed 's/ /_/'`)

    diff_start_to_end=$(echo "$end_timestamp-$start_timestamp" | bc -l)

    if [ $diff_start_to_end -ge 86400 ]
    then
        while [ `expr "$diff_start_to_end/86400"` -ge 1 ]
        do
            diff_start_to_end=$((diff_start_to_end-86400))
            spent_hour=$((spent_hour+24))
        done
        
        # Second to Hour
        while [ `expr "$diff_start_to_end/3600"` -ge 1 ]
        do
            diff_start_to_end=$((diff_start_to_end-3600))
            spent_hour=$((spent_hour+1))
        done

        if [ -n $spent_hour]
        then
            spent_hour=$((spent_hour))
        else 
            spent_hour=0
        fi
        
        # Remaining Second to Minute
        while [ `expr "$diff_start_to_end/60"` -ge 1 ]
        do
            diff_start_to_end=$((diff_start_to_end-60))
            spent_minute=$((spent_minute+1))
        done

        echo "$spent_hour:$spent_minute:$diff_start_to_end"

    else
        # Second to Hour
        while [ `expr "$diff_start_to_end/3600"` -ge 1 ]
        do
            diff_start_to_end=$((diff_start_to_end-3600))
            spent_hour=$((spent_hour+1))
        done
        if [ -n $spent_hour ]
        then
            spent_hour=$((spent_hour))
        else 
            spent_hour=0
        fi
        
        # Remaining Second to Minute
        while [ `expr "$diff_start_to_end/60"` -ge 1 ]
        do
            diff_start_to_end=$((diff_start_to_end-60))
            spent_minute=$((spent_minute+1))
        done

        echo $(leading_zero_fill $spent_hour 2)":"$(leading_zero_fill $spent_minute 2)":"$(leading_zero_fill $diff_start_to_end 2)

    fi
}
