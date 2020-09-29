print_help () {
  ECHO "insert_data.sh: periscope setup script"
  ECHO "-t|--type REQUIRED"
  ECHO "     type of periscope called (event, alert, table_info)"
  ECHO ""
}

insert_data() {
    SOURCE_FILE=$1
    TARGET_TABLE=$2
    LOG_FILE=$3

    tsload \
      --source_file ${SOURCE_FILE} \
      --target_database TS_CUSTOM_PERISCOPE_SERVICE_DB \
      --target_table ${TARGET_TABLE} \
      --has_header_row \
      --field_separator \| \
      --null_value "" \
      --boolean_representation True_False \
      --date_time_format "%Y-%m-%d %H:%M:%S.%f" \
    >> ${LOG_FILE} 2>&1

}


if [ -z "$*" ]; then
  log_it "ERROR" "no arguments provided"
  print_help
  exit 1
fi


insert_data $*
