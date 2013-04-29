#!/bin/bash

perm=perm0

rm show_4-round_$perm\_train.csv
rm show_4-round_$perm\_test.csv
rm noshow_4-round_$perm\_train.csv
rm noshow_4-round_$perm\_test.csv

for dir in */;
do
    cat ./$dir/$perm/training_4-rounds_showdown.csv >> show_4-round_$perm\_train.csv;
    cat ./$dir/$perm/test_4-rounds_showdown.csv >> show_4-round_$perm\_test.csv;
    cat ./$dir/$perm/training_4-rounds_no-showdown.csv >> noshow_4-round_$perm\_train.csv;
    cat ./$dir/$perm/test_4-rounds_no-showdown.csv >> noshow_4-round_$perm\_test.csv;
done
