####################################################################################
# Function Definitions

function julian_to_gregorian(date_in){

    if(length(date_in) == 7){
        julian_days=substr(date_in,5,3)
    }else{
        julian_days=substr(date_in,3,3)
    }

    julian_years=substr(date_in,1,length(date_in)-3)

    if(length(julian_years) > 2)
        gregorian_year=julian_years
    else
        gregorian_year="20"julian_years

    if((gregorian_year%4) == 0)
        month_index[2]=29
    else
        month_index[2]=28

    month_index[1]=31
    month_index[3]=31
    month_index[4]=30
    month_index[5]=31
    month_index[6]=30
    month_index[7]=31
    month_index[8]=31
    month_index[9]=30
    month_index[10]=31
    month_index[11]=30
    month_index[12]=31

    passed_julian_date=(julian_days*1)
    total_days=0
    for(i=1;i<=12;i++){
        if(total_days < passed_julian_date){
            total_days=(total_days+month_index[i])
            mounth=i
        }
    }

    calc_day=(month_index[mounth]-(total_days-passed_julian_date))

    return gregorian_year"-"substr(mounth,1 + length(mounth) - 3)"-"substr(calc_day,1 + length(calc_day) - 3)

}

function convert_time(time_in){
    if(index(time_in,":") > 0){
        split(time_in,time_arr,":")
        split(time_arr[3],time_arr_sec,".")
        return time_arr[1]":"time_arr[2]":"time_arr_sec[1]
    }else{
        hour_parsed=substr(time_in,1,2)
        minute_parsed=substr(time_in,3,2)
        second_parsed=substr(time_in,5,2)
        return hour_parsed":"minute_parsed":"second_parsed
    }
}

function ipled_convert_time(time_in){
    split(time_in,time_piece,".")
    return time_piece[1]":"time_piece[2]":"time_piece[3]
}


function ipled_convert_date(date_in){
    split(date_in,date_piece,"/")
    return date_piece[3]"-"date_piece[1]"-"date_piece[2]
}

function csv_output(log_name, log_id, date, time, system_name_in, type, error, last_ipl, msg){
        print log_name";"log_id";"julian_to_gregorian(date)";"convert_time(time)";"system_name_in";"type";"error";"last_ipl";"msg
}

BEGIN {
    ################################################################################
    # Parsers variables
    pre_ipl="IPLTRK01I"
    pos_ipl="IPLTRK02I"
    system_ipled="SYSTEM IPLED"
    split("TSO IS SHUTTING DOWN|DSI039I",start_of_shutdown,"|")
    split("Z EOD|IXC371D|JES2 TERMINATION COMPLETE|PJES2|P JES2|JES3 IS AUTODOWN|JES3|IEF404I",end_of_shutdown,"|")
    start_of_ipl="IEA371I"
    split("HZS0103I|S TN3270|S SSHD",end_of_ipl,"|")
    errors_list="ERROR|UNAUTHORIZED|ABEND|NOT FOUND|NOT DEFINED|PROBLEM|INSUFFICIENT"
}

{
if ($6 ~ /:/){
    if ($4 ~ system_name) {
        if ($0 ~ start_of_shutdown[1] || $0 ~ start_of_shutdown[2]){
                csv_output(original_name_file,$1,$5,$6,system_name,"SHUTDOWN BEGIN","null",$0)
            }

            else if ($0 ~ end_of_shutdown[1] || $0 ~ end_of_shutdown[2] || $0 ~ end_of_shutdown[3] || $0 ~ end_of_shutdown[4] || $0 ~ end_of_shutdown[5] || $0 ~ end_of_shutdown[6] || ($0 ~ end_of_shutdown[7] && $9 ~ end_of_shutdown[8])){
                csv_output(original_name_file,$1,$5,$6,system_name,"END OF SHUTDOWN","null",$0)
            }

            else if ($0 ~ start_of_ipl){
                csv_output(original_name_file,$1,$5,$6,system_name,"IPL BEGIN","null",$0)
            }

            else if ($0 ~ end_of_ipl[1] || $0 ~ end_of_ipl[2] || $0 ~ end_of_ipl[3]){
                csv_output(original_name_file,$1,$5,$6,system_name,"IPL END","null",$0)
            }

            else if ($0 ~ pre_ipl){
                csv_output(original_name_file,$1,$5,$6,system_name,"PRE IPL","null",$0)
            }

            else if ($0 ~ pos_ipl){
                csv_output(original_name_file,$1,$5,$6,system_name,"POST IPL","null",$0)
            }

            else if (match($0, errors_list) != 0){
                csv_output(original_name_file,$1,$5,$6,system_name,"null","y",$0)
            }

            else{
                csv_output(original_name_file,$1,$5,$6,system_name,"null","null",$0)
            }
    }
}

##
else if ($0 ~ system_ipled) {
    date = ipled_convert_date($10);
    time = ipled_convert_time($8);
    print system_name" "date " " time > "/u/aotools/teste.txt";
    csv_output(original_name_file, "null", "null", "null", system_name, "SYSTEM IPLED", "null", date " " time, $0);
        }

##

else if ($5 ~ /:/ && $2 !~ /\011DR|\011S|\011E|\011D|\011ER|\011LR/){
    if ($3 ~ system_name){
        if ($0 ~ start_of_shutdown[1] || $0 ~ start_of_shutdown[2]){
            csv_output(original_name_file,$1,$4,$5,system_name,"SHUTDOWN BEGIN","null",$0)
        }

        else if ($0 ~ end_of_shutdown[1] || $0 ~ end_of_shutdown[2] || $0 ~ end_of_shutdown[3] || $0 ~ end_of_shutdown[4] || $0 ~ end_of_shutdown[5] || $0 ~ end_of_shutdown[6] || ($0 ~ end_of_shutdown[7] && $9 ~ end_of_shutdown[8])){
            csv_output(original_name_file,$1,$4,$5,system_name,"END OF SHUTDOWN","null",$0)
        }

        else if ($0 ~ start_of_ipl){
            csv_output(original_name_file,$1,$4,$5,system_name,"IPL BEGIN","null",$0)
        }

        else if ($0 ~ end_of_ipl[1] || $0 ~ end_of_ipl[2] || $0 ~ end_of_ipl[3]){
            csv_output(original_name_file,$1,$4,$5,system_name,"IPL END","null",$0)
        }

        else if ($0 ~ pre_ipl){
            csv_output(original_name_file,$1,$4,$5,system_name,"PRE IPL","null",$0)
        }

        else if ($0 ~ pos_ipl){
            csv_output(original_name_file,$1,$4,$5,system_name,"POST IPL","null",$0)
        }

        else if (match($0, errors_list) != 0){
            csv_output(original_name_file,$1,$4,$5,system_name,"null","y",$0)
        }

        else{
            csv_output(original_name_file,$1,$4,$5,system_name,"null","null",$0)
        }
    }
}

else if ($6 ~ /R=/ && $2 !~ /\011DR|\011S|\011E|\011D|\011ER|\011LR/){
    if ($0 ~ start_of_shutdown[1] || $0 ~ start_of_shutdown[2]){
        csv_output(original_name_file,$1,$3,$4,system_name,"SHUTDOWN BEGIN","null",$0)
    }

    else if ($0 ~ end_of_shutdown[1] || $0 ~ end_of_shutdown[2] || $0 ~ end_of_shutdown[3] || $0 ~ end_of_shutdown[4] || $0 ~ end_of_shutdown[5] || $0 ~ end_of_shutdown[6] || ($0 ~ end_of_shutdown[7] && $9 ~ end_of_shutdown[8])){
        csv_output(original_name_file,$1,$3,$4,system_name,"END OF SHUTDOWN","null",$0)
    }

    else if ($0 ~ start_of_ipl){
        csv_output(original_name_file,$1,$3,$4,system_name,"IPL BEGIN","null",$0)
    }

    else if ($0 ~ end_of_ipl[1] || $0 ~ end_of_ipl[2] || $0 ~ end_of_ipl[3]){
        csv_output(original_name_file,$1,$3,$4,system_name,"IPL END","null",$0)
    }

    else if ($0 ~ pre_ipl){
        csv_output(original_name_file,$1,$3,$4,system_name,"PRE IPL","null",$0)
    }

    else if ($0 ~ pos_ipl){
        csv_output(original_name_file,$1,$3,$4,system_name,"POST IPL","null",$0)
    }

    else if (match($0, errors_list) != 0){
        csv_output(original_name_file,$1,$3,$4,system_name,"null","y",$0)
    }

    else{
        csv_output(original_name_file,$1,$3,$4,system_name,"null","null",$0)
    }
}

else if ($3 ~ /^[[:digit:]]+$/ && $4 ~ /^[[:digit:]]+$/ && $2 !~ /\011DR|\011S|\011E|\011D|\011ER|\011LR/){
    if ($0 ~ start_of_shutdown[1] || $0 ~ start_of_shutdown[2]){
        csv_output(original_name_file,$1,$3,$4,system_name,"SHUTDOWN BEGIN","null",$0)
    }

    else if ($0 ~ end_of_shutdown[1] || $0 ~ end_of_shutdown[2] || $0 ~ end_of_shutdown[3] || $0 ~ end_of_shutdown[4] || $0 ~ end_of_shutdown[5] || $0 ~ end_of_shutdown[6] || ($0 ~ end_of_shutdown[7] && $9 ~ end_of_shutdown[8])){
        csv_output(original_name_file,$1,$3,$4,system_name,"END OF SHUTDOWN","null",$0)
    }

    else if ($0 ~ start_of_ipl){
        csv_output(original_name_file,$1,$3,$4,system_name,"IPL BEGIN","null",$0)
    }

    else if ($0 ~ end_of_ipl[1] || $0 ~ end_of_ipl[2] || $0 ~ end_of_ipl[3]){
        csv_output(original_name_file,$1,$3,$4,system_name,"IPL END","null",$0)
    }

    else if ($0 ~ pre_ipl){
        csv_output(original_name_file,$1,$3,$4,system_name,"PRE IPL","null",$0)
    }

    else if ($0 ~ pos_ipl){
        csv_output(original_name_file,$1,$3,$4,system_name,"POST IPL","null",$0)
    }

    else if (match($0, errors_list) != 0){
        csv_output(original_name_file,$1,$3,$4,system_name,"null","y",$0)
    }

    else{
        csv_output(original_name_file,$1,$3,$4,system_name,"null","null",$0)
    }
}

else if ($3 ~ /^[[:digit:]]+$/ && $2 !~ /\011DR|\011S|\011E|\011D|\011ER|\011LR/){

    if ($0 ~ start_of_shutdown[1] || $0 ~ start_of_shutdown[2]){
        csv_output(original_name_file,$1,$3,"null",system_name,"SHUTDOWN BEGIN","null",$0)
    }

    else if ($0 ~ end_of_shutdown[1] || $0 ~ end_of_shutdown[2] || $0 ~ end_of_shutdown[3] || $0 ~ end_of_shutdown[4] || $0 ~ end_of_shutdown[5] || $0 ~ end_of_shutdown[6] || ($0 ~ end_of_shutdown[7] && $9 ~ end_of_shutdown[8])){
        csv_output(original_name_file,$1,$3,"null",system_name,"END OF SHUTDOWN","null",$0)
    }

    else if ($0 ~ start_of_ipl){
        csv_output(original_name_file,$1,$3,"null",system_name,"IPL BEGIN","null",$0)
    }

    else if ($0 ~ end_of_ipl[1] || $0 ~ end_of_ipl[2] || $0 ~ end_of_ipl[3]){
        csv_output(original_name_file,$1,$3,"null",system_name,"IPL END","null",$0)
    }

    else if ($0 ~ pre_ipl){
        csv_output(original_name_file,$1,$3,"null",system_name,"PRE IPL","null",$0)
    }

    else if ($0 ~ pos_ipl){
        csv_output(original_name_file,$1,$3,"null",system_name,"POST IPL","null",$0)
    }

    else if (match($0, errors_list) != 0){
        csv_output(original_name_file,$1,$3,"null",system_name,"null","y",$0)
    }

    else{
        csv_output(original_name_file,$1,$3,"null",system_name,"null","null",$0)
    }
}

else if ($4 ~ /^[[:digit:]]+$/ && $5 ~ /^[[:digit:]]+$/){
    
    if ($0 ~ start_of_shutdown[1] || $0 ~ start_of_shutdown[2]){
        csv_output(original_name_file,$1,$4,$5,system_name,"SHUTDOWN BEGIN","null",$0)
    }

    else if ($0 ~ end_of_shutdown[1] || $0 ~ end_of_shutdown[2] || $0 ~ end_of_shutdown[3] || $0 ~ end_of_shutdown[4] || $0 ~ end_of_shutdown[5] || $0 ~ end_of_shutdown[6] || ($0 ~ end_of_shutdown[7] && $9 ~ end_of_shutdown[8])){
        csv_output(original_name_file,$1,$4,$5,system_name,"END OF SHUTDOWN","null",$0)
    }

    else if ($0 ~ start_of_ipl){
        csv_output(original_name_file,$1,$4,$5,system_name,"IPL BEGIN","null",$0)
    }

    else if ($0 ~ end_of_ipl[1] || $0 ~ end_of_ipl[2] || $0 ~ end_of_ipl[3]){
        csv_output(original_name_file,$1,$4,$5,system_name,"IPL END","null",$0)
    }

    else if ($0 ~ pre_ipl){
        csv_output(original_name_file,$1,$4,$5,system_name,"PRE IPL","null",$0)
    }

    else if ($0 ~ pos_ipl){
        csv_output(original_name_file,$1,$4,$5,system_name,"POST IPL","null",$0)
    }

    else if (match($0, errors_list) != 0){
        csv_output(original_name_file,$1,$4,$5,system_name,"null","y",$0)
    }

    else{
        csv_output(original_name_file,$1,$4,$5,system_name,"null","null",$0)
    }
}

else{
    csv_output(original_name_file,$1,"null","null",system_name,"null","null",$0)
}
}