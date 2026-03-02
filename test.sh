#sh!

management_command="create_algorithm_input"
symbol="BTC"

start_year=2024
start_month=10
current_year=$(date +%Y)
current_month=$(date +%m)

year=$start_year
month=$start_month

while [ "$year" -lt "$current_year" ] || { [ "$year" -eq "$current_year" ] && [ "$month" -le "$current_month" ]; }; do
   for day in {1..31}; do
      if date -j -f "%Y-%m-%d" "$year-$month-$day" >/dev/null 2>&1; then
         if [ "$(date -j -f "%Y-%m-%d" "$year-$month-$day" +%u)" -eq 1 ]; then
            python manage.py create_algorithm_input --year $year --month $month --day $day --symbol $symbol
            python manage.py create_lvl2_algorithm_input --year $year --month $month --day $day --symbol $symbol
         fi
      fi
   done

   if [ "$month" -eq 12 ]; then
      month=1
      year=$((year + 1))
   else
      month=$((month + 1))
   fi
done
