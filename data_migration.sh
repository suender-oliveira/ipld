#!/bin/bash

cd /zplatipld/results/import
lista=$(cat IMPORT_resume.CSV | cut -d";" -f1 | sort | uniq | grep -v sysname)



for i in $lista
    do
        cat IMPORT_resume.CSV | grep sysname > /zplatipld/results/import/new_ones/"$i"_resume.CSV
        cat IMPORT_resume.CSV | grep $i >> /zplatipld/results/import/new_ones/"$i"_resume.CSV
    done
cat IMPORT_resume.CSV | grep sysname > /zplatipld/results/import/new_ones/empty_resume.CSV