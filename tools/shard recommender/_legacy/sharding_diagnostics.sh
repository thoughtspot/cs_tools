#!/bin/bash
tmp_file="/tmp/stats.txt"
echo "show statistics for server;" | tql 2&> $tmp_file
# Column Order for reference:
#
# Database_Name=1
# Schema_Name=2
# Table Name=3
# Table Guid=4
# Status=5
# Serving_Timestamp=6
# Total_Row_Count=7
# Row_Count_Skew =8
# Estimated_Size=9
# Estimated_Size_Skew=10
# Total_Shards_=11
# Cluster_Space_Used=12
# Last_Updated_Timestamp=13


# UnderSharding: Number of Shards < 512 AND row_count/num_regions > 20M

echo ""
echo "========================="
echo ""
echo "UnderSharded Tables"
echo "-------------------"
echo -e "TableName\\tTableGuid\tNumber of Shards\tNumber of Rows\tRows per region"
awk -F\| '{if ($11 > 0 && $11 < 512 && ($7/$11) > 20000000) {printf "%s\t%s\t%d\t%d\t%d\n",$3,$4,$11,$7,($7/$11) }}' $tmp_file  | sort -nr -k5
echo ""
echo "========================="
echo ""


# Any table that is sharded into more than 8 shards,
# but the number of shards per row is less than 2 million.
echo "OverSharded Tables"
echo "-------------------"
echo -e "TableName\tTableGuid\tNumber of Shards\tNumber of Rows\tRows per region"
awk -F\| '{if ($11 > 8 && $11 <512  && $11 < 512 && $7 > 0 &&($7/$11) < 2000000) \
             {printf "%s\t%s\t%d\t%d\t%d\n",$3,$4,$11,$7,($7/$11) }}' $tmp_file  | sort -n -k5
echo ""
echo "========================="
echo ""


# Any table with Skew more than 30% and skew in memory space > 20G.
# skew is (max - min), we see if (max - min)/avg > 0.3
echo "Skewed Tables (Memory)"
echo "-------------------"
echo -e "TableName\tTableGuid\tTotal Size (MB)\tSkew Size\tSkew Percentage\t"
awk -F\| '{if ($9 > 1 && $10 > 20480 && (($10 * $11)/($9 + 0.001)) > 0.30) \
             {printf "%s\t%s\t%d\t%d\t%d %\n",$3,$4,$9,$10,(100*$10*$11/($9 + 0.001)) }}' $tmp_file  | sort -nr  -k5

# Any table with Skew more than 30% with respect to average and more than 3 million.
echo ""
echo "Skewed Tables (Rows)"
echo "-------------------"
echo -e "TableName\tTableGuid\tTotal Row Count\tSkew Row Count\tRows per region\tSkew Percentage\t"
awk -F\| '{if ($7 > 1 && $11 > 1 && $8 > 3000000 && (($8 * $11)/($7 + 0.001)) > 0.30) \
             {printf "%s\t%s\t%d\t%d\t%d\t%d %\n",$3,$4,$7,$8,($7/$11),(100*$8 * $11/($7 + 0.001)) }}' $tmp_file  | sort -nr  -k7
