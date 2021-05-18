insert_data () {
    SOURCE_FILE=$1
    TARGET_TABLE=$2

    tsload \
      --source_file ${SOURCE_FILE} \
      --target_database cs_tools \
      --target_table ${TARGET_TABLE} \
      --has_header_row \
      --field_separator "," \
      --null_value "" \
      --boolean_representation True_False \
      --date_time_format "%Y-%m-%dT%H:%M:%S" \
      --empty_target
}


for file in $1; do
    SOURCE_FILE=$(echo "${file}")
    TARGET_TABLE=$(basename ${file} .csv)
    insert_data ${SOURCE_FILE} ${TARGET_TABLE}
done
