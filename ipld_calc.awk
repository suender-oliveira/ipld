 ####################################################################################
# Function Definitions

function date_to_epoch(date_time_in){

    split(date_time_in,date_time_arr," ")
    split(date_time_arr[1],date_arr,"-")
    split(date_time_arr[2],time_arr,":")

    return timestamp_unix=(((date_arr[1] - 1970) * 31557600) + (date_arr[2] * 2629800) + (date_arr[3] * 86400) + (time_arr[1] * 3600) + (time_arr[2] * 60) + second=time_arr[3])
}

function calc_time_cli(start_tt,end_tt){

    start_timestamp = date_to_epoch(start_tt)
    end_timestamp = date_to_epoch(end_tt)

    diff_start_to_end=(end_timestamp - start_timestamp)
    spent_hour=0
    spent_minute=0

    if (diff_start_to_end > 86400){

        while ((diff_start_to_end / 86400) >= 1){
            diff_start_to_end=(diff_start_to_end - 86400)
            spent_hour=(spent_hour + 24)
        }

        # Second to hour
        while ((diff_start_to_end / 3600) >= 1){
            diff_start_to_end=(diff_start_to_end - 3600)
            spent_hour=(spent_hour + 1)
        }

        # Remaining seconds to minute
        while ((diff_start_to_end / 60) >= 1){
            diff_start_to_end=(diff_start_to_end - 60)
            spent_minute=(spent_minute + 1)
        }

        calculated_time=sprintf("%02d:%02d:%02d", spent_hour,spent_minute,diff_start_to_end)
        return calculated_time
    }
    else{

        # Second to hour
        while ((diff_start_to_end / 3600) >= 1){
            diff_start_to_end=(diff_start_to_end - 3600)
            spent_hour=(spent_hour + 1)
        }

        # Remaining seconds to minute
        while ((diff_start_to_end / 60) >= 1){
            diff_start_to_end=(diff_start_to_end - 60)
            spent_minute=(spent_minute + 1)
        }

        calculated_time=sprintf("%02d:%02d:%02d", spent_hour,spent_minute,diff_start_to_end)
        return calculated_time
    }
}

BEGIN {
    ################################################################################
    # Parsers variables
    errors_list="ERROR|UNAUTHORIZED|ABEND|NOT FOUND|NOT DEFINED|PROBLEM|INSUFFICIENT"
}

{
    ####################################################################################
    # Start processing

    if (match($0, "SHUTDOWN BEGIN") != 0 || match($0, "END OF SHUTDOWN") != 0 || match($0, "IPL BEGIN") != 0 || match($0, "IPL END") != 0 || match($0, "PRE IPL") != 0 || match($0, "POST IPL") != 0 || match($0, "SYSTEM IPLED") != 0){
        if (match($0, "SHUTDOWN BEGIN") != 0){
            start_shutdown_current_time = $3" "$4
            if (start_shutdown_time_line == "" || start_shutdown_current_time < start_shutdown_time_line){
                start_shutdown_time_line = start_shutdown_current_time
            }
        }
        else if (match($0, "END OF SHUTDOWN") != 0){
            end_shutdown_current_time = $3" "$4
            if ((end_shutdown_time_line == "" || end_shutdown_current_time < end_shutdown_time_line) && (end_shutdown_current_time > start_shutdown_time_line)){
                end_shutdown_time_line = end_shutdown_current_time
            }
        }
        else if (match($0, "IPL BEGIN") != 0){
            start_ipl_current_time = $3" "$4
            if ((start_ipl_time_line == "" || start_ipl_current_time < start_ipl_time_line) && (start_ipl_current_time > end_shutdown_time_line)){
                start_ipl_time_line = start_ipl_current_time
            }
        }
        else if (match($0, "IPL END") != 0){
            end_ipl_current_time = $3" "$4
            if ((end_ipl_time_line == "" || end_ipl_current_time > end_ipl_time_line) && (end_ipl_current_time > start_ipl_time_line)){
                end_ipl_time_line = end_ipl_current_time
            }
        }
        else if (match($0, "PRE IPL") != 0){
            pre_ipl_current_time = $3" "$4
            if (pre_ipl_time_line == "" || pre_ipl_current_time < pre_ipl_time_line){
                pre_ipl_time_line = pre_ipl_current_time
            }
            
        }
        else if (match($0, "POST IPL") != 0){
            pos_ipl_current_time = $3" "$4
            if (pos_ipl_time_line == "" || pos_ipl_current_time > pos_ipl_time_line){
                pos_ipl_time_line = pos_ipl_current_time
            }
        }
        else if (match($0, "SYSTEM IPLED") != 0){

            end_ipled_time = $8
            if (end_ipled_time_line == "" || end_ipled_current_time > end_ipled_time_line){
                end_ipled_current_time = end_ipled_time
            }
        }
    }
}

END{
    ####################################################################################
    # Elapsed time between pre-ipl and start of shutdown
    if (length(start_shutdown_time_line) <= 0 || length(pre_ipl_time_line) <= 0){
        elapsed_before_shutdown=""
    }
    else{
        elapsed_before_shutdown=calc_time_cli(pre_ipl_time_line,start_shutdown_time_line)
    }

    ####################################################################################
    # Elapsed time between start of shutdown and end of shutdown
    if (length(start_shutdown_time_line) <= 0 || length(end_shutdown_time_line) <= 0){
        elapsed_after_shutdown=""
    }
    else{
        elapsed_after_shutdown=calc_time_cli(start_shutdown_time_line,end_shutdown_time_line)
    }

    ####################################################################################
    # Elapsed time between end of shutdown and start of ipl
    if (length(end_shutdown_time_line) <= 0 || length(start_ipl_time_line) <= 0){
        elapsed_btn_shut_ipl=""
    }
    else{
        elapsed_btn_shut_ipl=calc_time_cli(end_shutdown_time_line,start_ipl_time_line)
    }

    ####################################################################################
    # Elapsed time between start of ipl and end of ipl
    if (length(start_ipl_time_line) <= 0 || length(end_ipl_time_line) <= 0){
        elapsed_ipl=""
    }
    else{
        elapsed_ipl=calc_time_cli(start_ipl_time_line,end_ipl_time_line)
    }

    ####################################################################################
    # Elapsed time between end of ipl and start of pos-ipl
    if (length(end_ipl_time_line) <= 0 || length(pos_ipl_time_line) <= 0){
        elapsed_after_ipl=""
    }
    else{
        elapsed_after_ipl=calc_time_cli(end_ipl_time_line,pos_ipl_time_line)
    }

    ####################################################################################
    # Total elapsed time
    if (length(pre_ipl_time_line) <= 0 || length(pos_ipl_time_line) <= 0){
        total_elapsed=""
    }
    else{
        total_elapsed=calc_time_cli(pre_ipl_time_line,pos_ipl_time_line)
    }
 
    if (length(pre_ipl_time_line) > 0 || 
        length(start_shutdown_time_line) > 0 || 
        length(end_shutdown_time_line) > 0 || length(start_ipl_time_line) > 0 || 
        length(end_ipl_time_line) > 0 || 
        length(pos_ipl_time_line) > 0 )
        {
        print system_name";"log_dataset";"pre_ipl_time_line";"start_shutdown_time_line";"end_shutdown_time_line";"start_ipl_time_line";"end_ipl_time_line";"pos_ipl_time_line";"";"elapsed_before_shutdown";"elapsed_after_shutdown";"elapsed_btn_shut_ipl";"elapsed_ipl";"elapsed_after_ipl";"total_elapsed
    }
    else{
        print system_name";"log_dataset";"";"";"";"";"";"";"end_ipled_current_time";"";"";"";"";"";"
    }
    
}