%for computing P(A) priors from the EM learned CPT tables

%CPT3,6,9,12 loaded

%from globles.py
bucket_percentiles3 =  [0.40003900044927887, 0.24004940056908658, 0.14407297417398401, 0.08651600755861058, 0.05202997629219996, 0.03141860537037599, 0.019185529213985624, 0.012068594181324752, 0.008169950930350486, 0.006449961260803015];
bucket_percentiles6 =  [0.25000586640034034, 0.18750635526703532, 0.1406323737393166, 0.10547775668987426, 0.07911295269792144, 0.059340894764128745, 0.04451391139401344, 0.033396420640065934, 0.025061964939457244, 0.01881600631713666, 0.01413804822124413, 0.010638260810455278, 0.008024995133871034, 0.0060804790517760415, 0.004642669557329053, 0.003591749192659485, 0.0028401412607115414, 0.0023252117671562263, 0.0020040499208639297, 0.0018498922346436276];
bucket_percentiles9 =  [0.3000164218894933, 0.21001853327528525, 0.14702302751075672, 0.10293048242618265, 0.07207185651068919, 0.05047961214657008, 0.035377603629867124, 0.02482414415128994, 0.017462360349307173, 0.012345737163663904, 0.00881642304192028, 0.006420649025566406, 0.004850387026785357, 0.003903746217162425, 0.0034590156354603763];
bucket_percentiles12 = [0.3501610588099545, 0.22769141220106134, 0.14813283943006045, 0.09649160947472483, 0.0630353366896258, 0.041458800434494715, 0.027695653492018392, 0.019152072015345536, 0.014217919495410875, 0.011963297957303649];

%%%%%%%%%%%%%%%%%%%%%%%

nbuckets = size(bucket_percentiles3,2);
joint_kk = bucket_percentiles3' * bucket_percentiles3;
num_actions = 1315;

PA3 = ones(1,num_actions);
for action=1:1315
    PA3(action) = sum(sum( CPT3( :, (action-1)*nbuckets+1 : action*nbuckets) .* joint_kk));
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

nbuckets = size(bucket_percentiles6,2);
joint_kk = bucket_percentiles6' * bucket_percentiles6;

PA6 = ones(1,num_actions);
for action=1:1315
    PA6(action) = sum(sum( CPT6( :, (action-1)*nbuckets+1 : action*nbuckets) .* joint_kk));
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

nbuckets = size(bucket_percentiles9,2);
joint_kk = bucket_percentiles9' * bucket_percentiles9;

PA9 = ones(1,num_actions);
for action=1:1315
    PA9(action) = sum(sum( CPT9( :, (action-1)*nbuckets+1 : action*nbuckets) .* joint_kk));
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

nbuckets = size(bucket_percentiles12,2);
joint_kk = bucket_percentiles12' * bucket_percentiles12;

PA12 = ones(1,num_actions);
for action=1:1315
    PA12(action) = sum(sum( CPT12( :, (action-1)*nbuckets+1 : action*nbuckets) .* joint_kk));
end

csvwrite( 'PA3.csv', PA3 );
csvwrite( 'PA6.csv', PA6 );
csvwrite( 'PA9.csv', PA9);
csvwrite( 'PA12.csv', PA12 );