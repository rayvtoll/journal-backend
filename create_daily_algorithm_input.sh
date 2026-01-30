#sh!

python manage.py get_ohlcv
python manage.py get_liquidations
python manage.py create_positions
python manage.py create_algorithm_input
cp data/algorithm_input-$(date +%Y-%m-%d)-live.csv data/algorithm_input-$(date +%Y-%m-%d)-reversed.csv ../traydingbot/algorithm_input/