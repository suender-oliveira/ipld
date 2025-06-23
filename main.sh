#!/bin/env sh
# Licensed Materials - Property of IBM
#
# (C) COPYRIGHT International Business Machines Corp. 2022
# All Rights Reserved
#
# US Government Users Restricted Rights - Use, duplication or
# disclosure restricted by GSA ADP Schedule Contract with IBM Corp.
####################################################################################

####################################################################################
# Exporting enviroment variables
export  TERM=vt100

####################################################################################
# Help Interface
display_help(){
    echo ""
    echo "Usage: main.sh [OPTION] ..."
    echo "This program will parsing SYSLOG data set to get information about the IPL process and its date and time for each process."
    echo ""
    echo "OPTIONS"
    echo ""
    echo "-h, will display this help"
    echo "-r, define the run mode for the program: \"alone\" or empty to run the user interface or \"cli\" to run in command line"
    echo ""
    echo "-q, setup the qualifier for SYSLOG file. e.g. SYSLOG.LPAR"
    echo "-o, by default the program will generating a CSV file with IPL information. To generate a JSON file inform this option followed by JSON."
    echo ""
    echo "Documentation and support is available at https://github.ibm.com/ao-zos-projects/ipl-log-analysis"
    echo ""
}

####################################################################################
# Function definition to calling the main program as an user interface
main(){
    ####################################################################################
    # Calling header function
    header
    
    ####################################################################################
    # Import methods
    if  [ -f methods.sh ]
    then
        . ./methods.sh
    else
        methods_custom=$(ls methods_*)
        . ./$methods_custom
    fi
    
    ####################################################################################
    # Calling for patterns
    defining_patterns
    
    ####################################################################################
    # Checking the input for syslog data set
    echo "Does the IPL SYSLOG data set splitted?"
    read splitted_datasets?"[ yes/no ]: "
    echo ""
    read config_dataset?"Enter config data set name: "
    echo ""
    case $splitted_datasets in
        yes)
            echo "Enter the data sets names with \"|\" between them"
            read syslog_dataset_names?"e.g. [SYSLOG.ZTD1.D221005.T235900|SYSLOG.ZTD1.D221006.T235900]: "
        ;;
        no)
            read syslog_dataset_names?"Enter the SYSLOG data set name: "
        ;;
        ?)
            echo "You should to enter the SYSLOG's data set name"
            break
        ;;
    esac
    echo ""
    
    ####################################################################################
    # Start of LOG processing
    echo "Starting log data set processing \t`date +%r" "%Z` ............................................. [ WAIT ]"
    
    if [ "$splitted_datasets" = "yes" ]
    then
        output_dataset=$(echo $syslog_dataset_names | cut -d"|" -f1 )
        [ -f $output_dataset.CSV ] && rm -rf "$output_dataset.CSV"
        echo "log_name;log_id;date;time;system;type;error;msg" > "$output_dataset.CSV"
        for i in $(echo $syslog_dataset_names | sed 's/\|/ /')
        do
            searchable_name_file="//'$i'"
            jes_level=$(nl $searchable_name_file | egrep "IEF237I" | awk '/JES/ && /ALLOCATED/ && /SYSLOG/' | awk '{print $10}' | uniq) > /dev/null 2>&1
            ipl_processor $i >> "$output_dataset.CSV"
        done
    else
        output_dataset=$(echo $syslog_dataset_names)
        [ -f $output_dataset.CSV ] && rm -rf "$output_dataset.CSV"
        echo "log_name;log_id;date;time;system;type;error;msg" > "$output_dataset.CSV"
        searchable_name_file="//'$syslog_dataset_names'"
        jes_level=$(cat $searchable_name_file | awk '/JES/ && /SYSLOG/' | awk '{print $9}' | uniq) > /dev/null 2>&1
        ipl_processor $output_dataset >> "$output_dataset.CSV"
    fi
    
    ####################################################################################
    # End of LOG processing
    echo "Completed log data set processing \t`date +%r" "%Z` ............................................. [ DONE ]"
    echo "Loading results \t\t\t`date +%r" "%Z` ............................................. [ WAIT ]"
    start_shutdown_time_line=$(grep 'SHUTDOWN BEGIN' $output_dataset.CSV | head -1)
    end_shutdown_time_line=$(grep 'END OF SHUTDOWN' $output_dataset.CSV | tail -1)
    start_ipl_time_line=$(grep 'IPL BEGIN' $output_dataset.CSV | head -1)
    end_ipl_time_line=$(grep 'IPL END' $output_dataset.CSV | head -1)
    echo "Results loaded \t\t\t\t`date +%r" "%Z` ............................................. [ DONE ]"
    echo ""
    echo ""
    echo "Shutdown starts at `echo $start_shutdown_time_line | awk -F";" '{print "\t"$3" "$4}'`"
    echo "Shutdown ends at `echo $end_shutdown_time_line | awk -F";" '{print "\t"$3" "$4}'`"
    shutdown_elapsed_time=$(calc_time "`echo $start_shutdown_time_line | awk -F";" '{print $3"_"$4}'`" "`echo $end_shutdown_time_line | awk -F";" '{print $3"_"$4}'`")
    echo "$shutdown_elapsed_time"
    echo ""
    echo "IPL starts at `echo $start_ipl_time_line | awk -F";" '{print "\t"$3" "$4}'`"
    echo "IPL ends at `echo $end_ipl_time_line | awk -F";" '{print "\t"$3" "$4}'`"
    ipl_elapsed_time=$(calc_time "`echo $start_ipl_time_line | awk -F";" '{print $3"_"$4}'`" "`echo $end_ipl_time_line | awk -F";" '{print $3"_"$4}'`")
    echo "$ipl_elapsed_time"
    echo ""
    total_elapsed_time=$(calc_time "`echo $start_shutdown_time_line | awk -F";" '{print $3"_"$4}'`" "`echo $end_ipl_time_line | awk -F";" '{print $3"_"$4}'`")
    echo "The elapsed time between start of shutdown and IPL end was $total_elapsed_time"
    echo ""
    echo "`tail -1 $output_dataset.CSV | cut -d';' -f2 ` lines were processed."
    echo "Your CSV file is available at `pwd`/$output_dataset.CSV"
    echo ""
    
    if [ $? -eq 0 ]
    then
        echo "Done."
    fi
}

####################################################################################
# Function definition to calling the main program as a command line interface
commnand_line(){
    
    ####################################################################################
    # Changing workdir based on received variables
    lpar_address=$(echo $opt_address | cut -d"." -f1 | tr '[:upper:]' '[:lower:]')
    work_dir="/tmp/ipl_analysis/$lpar_address"
    cd $work_dir
    
    ####################################################################################
    # Import methods
    if  [ -f methods.sh ]
    then
        . ./methods.sh
    else
        methods_custom=$(ls methods_*)
        . ./$methods_custom
    fi
    
    ####################################################################################
    # Calling for patterns
    defining_patterns
    
    ####################################################################################
    # Getting system name from z/OS
    system_name=$(/bin/sysvar SYSNAME)
    
    ####################################################################################
    # Issuing tso command to list all syslog data sets to parsing
    syslog_datasets_tso=$(tsocmd "listcat level($qualifier)" | grep -v "IN-CAT" | grep "LOG" | awk '{print $3}') > /dev/null 2>&1
    syslog_datasets_tso_count=$(echo "$syslog_datasets_tso" | wc -l)
    syslog_datasets_tso_limit=90
    
    if [ $syslog_datasets_tso_count -gt $syslog_datasets_tso_limit ]
    then
        syslog_datasets_tso_list=$(echo "$syslog_datasets_tso" | tail -$syslog_datasets_tso_limit)
    else
        syslog_datasets_tso_list=$syslog_datasets_tso
    fi
    
    ####################################################################################
    # Log processing
    for interation_datasets in $syslog_datasets_tso_list
    do
        
        [ -f $system_name"_"$interation_datasets".CSV" ] && rm -rf $system_name"_"$interation_datasets".CSV"
        echo "log_name;log_id;date;time;system;type;error;msg" > $system_name"_"$interation_datasets".CSV"
        searchable_name_file="//'$interation_datasets'"
        ipl_processor $interation_datasets >> $system_name"_"$interation_datasets".CSV"
        [ `cat $system_name"_"$interation_datasets".CSV" | awk -F';' '{print $6}' | egrep "SHUTDOWN*BEGIN|END*OF*SHUTDOWN|IPL|IPLED" | wc -l` = "0" ] && rm -rf $system_name"_"$interation_datasets".CSV"
    done
    
    list_full_csv=$(ls | grep $qualifier | grep -v resume)
    echo "sysname;log_dataset;pre_ipl;shutdown_begin;shutdown_end;ipl_begin;ipl_end;post_ipl;last_ipl;elapsed_before_shutdown;elapsed_after_shutdown;elapsed_btn_shut_ipl;elapsed_ipl;elapsed_after_ipl;total_elapsed" > $system_name"_"$qualifier"_resume.CSV"
    
    for list_csv in $list_full_csv
    do
        log_dataset=$(echo $list_csv | sed 's/.CSV//')
        
        cat $list_csv | awk -F";" -v system_name="$system_name" -v log_dataset="$log_dataset" -f ipld_calc.awk >> $system_name"_"$qualifier"_resume.CSV"
    done
}

####################################################################################
# Process to input options to program
while getopts "a:q:r:o:h" option
do
    case $option in
        h) help="$OPTARG"
            display_help
            exit
        ;;
        r) runner="$OPTARG"
        ;;
        a) opt_address="$OPTARG"
        ;;
        q) qualifier="$OPTARG"
        ;;
        o) output="$OPTARG"
        ;;
        ?) display_help
            exit 2
        ;;
    esac
done

if [ "$runner" = "" ] || [ "$runner" = "alone" ]
then
    main
elif [ "$runner" = "cli" ]
then
    commnand_line
fi