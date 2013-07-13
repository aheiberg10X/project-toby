%for computing P(A) priors from the EM learned CPT tables
%Also, for docotoring the probs so there are no P(A|k,k) = 0, 
%just close to it.  Write new CPT's out to CPT*_nozero.csv

em = 0

%CPT3,6,9,12 loaded

%from globles.py
bucket_percentiles3 =  [0.40003900044927887, 0.24004940056908658, 0.14407297417398401, 0.08651600755861058, 0.05202997629219996, 0.03141860537037599, 0.019185529213985624, 0.012068594181324752, 0.008169950930350486, 0.006449961260803015];
bucket_percentiles6 =  [0.25000586640034034, 0.18750635526703532, 0.1406323737393166, 0.10547775668987426, 0.07911295269792144, 0.059340894764128745, 0.04451391139401344, 0.033396420640065934, 0.025061964939457244, 0.01881600631713666, 0.01413804822124413, 0.010638260810455278, 0.008024995133871034, 0.0060804790517760415, 0.004642669557329053, 0.003591749192659485, 0.0028401412607115414, 0.0023252117671562263, 0.0020040499208639297, 0.0018498922346436276];
bucket_percentiles9 =  [0.3000164218894933, 0.21001853327528525, 0.14702302751075672, 0.10293048242618265, 0.07207185651068919, 0.05047961214657008, 0.035377603629867124, 0.02482414415128994, 0.017462360349307173, 0.012345737163663904, 0.00881642304192028, 0.006420649025566406, 0.004850387026785357, 0.003903746217162425, 0.0034590156354603763];
bucket_percentiles12 = [0.3501610588099545, 0.22769141220106134, 0.14813283943006045, 0.09649160947472483, 0.0630353366896258, 0.041458800434494715, 0.027695653492018392, 0.019152072015345536, 0.014217919495410875, 0.011963297957303649];


near_zero_prob = 10^-10;

%%%%%%%%%%%%%%%%%%%%%%%

num_actions = 1315;

for i=[3,6,9,12]
    
    if i == 3 
        CPT = CPT3;
        bucket_percentiles = bucket_percentiles3;
    elseif i == 6 
        CPT = CPT6;
        bucket_percentiles = bucket_percentiles6;
    elseif i == 9
        CPT = CPT9;
        bucket_percentiles = bucket_percentiles9;
    else 
        CPT = CPT12;
        bucket_percentiles = bucket_percentiles12;
    end
    
    nbuckets = size(bucket_percentiles,2);
    joint_kk = bucket_percentiles' * bucket_percentiles;

    PA = ones(1,num_actions);
    n_near_zero = 0;
    for action=1:1315
        CPT_nozero = (CPT == 0) .* near_zero_prob + CPT;
        Pa = sum(sum( CPT_nozero( :, (action-1)*nbuckets+1 : action*nbuckets) .* joint_kk));
        PA(action) = Pa;
    end
    
    csvwrite( sprintf('/home/andrew/project-toby/AK/em%d/PA%d.csv',em,i), PA );
    csvwrite( sprintf('/home/andrew/project-toby/AK/em%d/CPT%d_nozero.csv',em,i), CPT_nozero );

    
end

%we have added prob.  but not enough so that we really care?  or should we
%adjust?
%seem to be ~130484 0->near_zero_prob changes


