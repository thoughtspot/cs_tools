# import performance data
cat /tmp/stats.txt | sed '1d;3d' | sed 's/^ *//g' | sed 's/ *|/|/g' | sed 's/| */|/g' | sed 's/ *$//g' |  tsload --target_database TS_Performance_Analysis --has_header_row  --empty_target --csv --field_separator "|" --date_format "%m/%d/%y" --null_value "" --boolean_representation true_false --target_table TS_Table_Analysis --max_ignored_rows 1


