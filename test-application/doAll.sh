PATH=$PATH:.

ml local bootstrap
ml local restart

echo Sleeping for 10 seconds to allow for restart
sleep 10

ml local deploy modules
ml local deploy content
