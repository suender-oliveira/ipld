/* rexx */
rc = isfcalls("ON")
isflinelim=100000
cmd = "/D IPLINFO"

Address "SDSF" "ISFEXEC '"cmd"'"
Address SDSF "ISFLOG READ TYPE(SYSLOG)"

do i = 1 to isfline.0
  If pos('SYSTEM IPLED', isfline.i) <> 0 Then Do
    res = strip(isfline.i)
    say res
  End
End

rc = isfcalls("OFF")
exit
