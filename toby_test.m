dag_switch
test_show = 1
n_test_rows = 10000
smoothing = 0
%if we want to get accuracy doing no prediction
computing_baseline = 0
uniform = 0

%for testing river belief buckets ONLY
if test_show == 1
    test_all = csvread('../../project-toby/nodes/show_4-round_perm0_test_merged.csv');
else
    test_all = csvread('../../project-toby/nodes/noshow_4-round_perm0_test_merged.csv');
end

test = test_all(1:n_test_rows,1:N);
amts = test_all(1:n_test_rows,N+1);
[ncases,natt] = size(test);

%shit, we printed all -1, but we want the true label for testing
%should reparse, printing everything, and use a hand-input visible mask
%visible_ixs = find( test(0,:) >= 0 );
if dag_switch == 1 || dag_switch == 2 
    visible_ixs = [12 13 14 15];
else
    visible_ixs = [6 9 12 13 14 15];
end


%we want to be able to exclude arbitrary types of hands from evaluation
%for examples, it is easy to get good accuacy by predicting check every time
%what is our prediction rate for the hands that do not have all checks?
focus_nodes = [12 13 14 15];
special_focus_values = []; %[20 20 1 3 4 12]; %; [1 3 5 8]; [1 3 4 8]];
%can ignore focus, and include all else
%or include all else, and ignore focus
ignore_special_focus = 1;
n_not_excluded = 0;

engine = jtree_inf_engine(bnet_learned);

%which node are we trying to predict?
predict_node1 = 10;
predict_node2 = 11;  %or 11
n_river_buckets = 10;

%for each test hand, we will get a distribution over buckets
%we will sample this dist k times, and compute the average difference
%between this sample and the true label
%add this average difference for each hand to avg_distance_sum
avg_diff_sum1 = 0;
avg_diff_sum2 = 0;
avg_weighted_diff_sum1 = 0;
avg_weighted_diff_sum2 = 0;

%sum of how likely we are to get the exact pocket correct
avg_p_correct_pocket1 = 0;
avg_p_correct_pocket2 = 0;

avg_p_correct_winner = 0;
avg_weighted_correct_winner = 0;


%count how many test examples were not seen when training
%the marginal distribution for these examples is set to all 0's
novel_count = 0;

%s=struct(bnet_learned.CPD{predict_nod e});  % violate object privacy
%predict_prior = s.CPT;
if scaling == 1
    predict_prior = [0.2340    0.1782    0.1384    0.1211    0.0986    0.0706    0.0522    0.0416    0.0306    0.0345];
else 
    predict_prior = [0.3752    0.2762    0.1611    0.0736    0.0369    0.0299    0.0183    0.0126    0.0081    0.0081];
   % [ 0.00809088803483 0.00805163093616 0.0126211572208 0.0183409164962 0.0299178348925  0.0369213012943  0.0736070599966 0.161064024402 0.276201169076 0.37518401765]
end

for ex=1:n_test_rows
    if mod(ex,1000) == 0
        ex
    end

    %do not evaluate the rows where the specified nodes take on 
    %specifics values
    focus_values = test(ex,focus_nodes);
    in_focus = sum(ismember( special_focus_values, focus_values, 'rows' ));
    should_ignore = ~xor(in_focus,ignore_special_focus);
    if( should_ignore )
        continue;
    end

    n_not_excluded = n_not_excluded + 1;

    %turn the data into a cell array evidence, turning all values not
    %marked as visible into []
    evidence = cell(1,N);
    evidence( :,visible_ixs ) = num2cell( test(ex,visible_ixs) );

    %get rid of the dummy values as well
%    active_values = test(i,[12 13 14 15]);
%    dummy_ix_offsets = find(active_values == 8);
%        evidence{11+ix} = [];
%    end
    
    true_label1 = test(ex,predict_node1);
    true_label2 = test(ex,predict_node2);
    
    n_samples = 200;
    marginal = zeros(1,n_river_buckets);
    if( ~computing_baseline )
        %get the distribution over the outcomes of predict_node
        [engine2, ll] = enter_evidence(engine, evidence);
        marg1 = marginal_nodes(engine2, predict_node1);
        marg2 = marginal_nodes(engine2, predict_node2);

        evidence;
        marginal1 = marg1.T;
        marginal2= marg2.T;
        true_label1;
        true_label2;

        %v = test(i,visible_ixs);
        %my_marginal = P10gactive(bnet_learned, v(1), v(2), v(3), v(4));
        
        %if this instance wasn't in training, it will be all zeros
        %use a uniform prior instead
        if( sum(marginal1) < .99 )
            marginal1 = predict_prior;
            novel_count = novel_count + 1;
        end
        if( sum(marginal2) < .99 )
            marginal2 = predict_prior;
            novel_count = novel_count + 1;
        end
        %bound
        if smoothing 
            assert(false);
            meen = mean(marginal .* 1:n_river_buckets);
            sigma = std(marginal .* 1:n_river_buckets);
            samples = round(normrnd(meen,sigma,1,n_samples));
            predicted_buckets = samples(samples >= 1 & samples <= n_river_buckets);
        else 
            predicted_buckets1 = discretesample( marginal1, n_samples );
            predicted_buckets2 = discretesample( marginal2, n_samples );

        end
    else
        %evidence;
        %if uniform == 0 
        %    if dag_switch == 4 
        %        marginal = predict_prior(evidence{6}, evidence{9}, evidence{12}, evidence{13}, :);
        %    else
        %        marginal = predict_prior;
        %    end
        %else
        %    marginal = ones(1,n_river_buckets) / n_river_buckets;
        %end
%
%        if( sum(marginal) < .99 )
%        end
        if uniform 
            marginal1 = ones(1,n_river_buckets) / n_river_buckets;
            marginal2 = ones(1,n_river_buckets) / n_river_buckets;
        else 
            %prior = [0.0345359529904 0.0306354399597 0.041614205203 0.0522462239304 0.0706207070855 0.0986177913326 0.121145527201 0.138365729732 0.178227709208 0.233990713358];
            marginal1 = predict_prior; 
            marginal2 = predict_prior; 
        end
        predicted_buckets1 = discretesample( marginal1, n_samples );
        predicted_buckets2 = discretesample( marginal2, n_samples );
    end

    diff_sum1 = 0;
    diff_sum2 = 0;
    n_samples = min(size(predicted_buckets1,2), size(predicted_buckets2,2));
    one_wins = 0;
    for i=1:n_samples
        pb1 = predicted_buckets1(i);
        pb2 = predicted_buckets2(i);
        if pb1 > pb2 
            one_wins = one_wins + 1;
        elseif pb1 < pb2
            one_wins;
        else
            one_wins = one_wins + .5;
        end

        a = pb1;
        b = true_label1;
        diff1 = bucketCentroidDistance(a,b);
        diff_sum1 = diff_sum1 + diff1;

        a = pb2;
        b = true_label2;
        diff2 = bucketCentroidDistance(a,b);
        diff_sum2 = diff_sum2 + diff2;
    end
    %average the samples differences from true_label
    %weight them by amt_exchanged
    avg_diff1 = diff_sum1 / n_samples;
    avg_weighted_diff1 = avg_diff1 * amts(ex);
    
    avg_diff2 = diff_sum2 / n_samples;
    avg_weighted_diff2 = avg_diff2 * amts(ex);

    %add the averages to the total to average over all training examples
    avg_diff_sum1 = avg_diff_sum1 + avg_diff1;
    avg_weighted_diff_sum1 = avg_weighted_diff_sum1 + avg_weighted_diff1;
    
    avg_diff_sum2 = avg_diff_sum2 + avg_diff2;
    avg_weighted_diff_sum2 = avg_weighted_diff_sum2 + avg_weighted_diff2;

    p_correct_bucket1 = marginal1(true_label1);
    p_correct_bucket2 = marginal2(true_label2);
    percentiles = [0.3501610588099545, 0.22769141220106134, 0.14813283943006045, 0.09649160947472483, 0.0630353366896258, 0.041458800434494715, 0.027695653492018392, 0.019152072015345536, 0.014217919495410875, 0.011963297957303649];

    p_correct_pocket1 = p_correct_bucket1 * 1 / (1081*percentiles(true_label1));
    avg_p_correct_pocket1 = avg_p_correct_pocket1 + p_correct_pocket1;
    
    p_correct_pocket2 = p_correct_bucket2 * 1 / (1081*percentiles(true_label2));
    avg_p_correct_pocket2 = avg_p_correct_pocket2 + p_correct_pocket2;

    avg_one_wins = one_wins/n_samples;
    if true_label1 > true_label2
        p_correct_winner = avg_one_wins;
    elseif true_label1 < true_label2
        p_correct_winner = (1 - avg_one_wins);
    else
        p_correct_winner = .5;  %1 - abs(.5 - avg_one_wins);

    end
    p_correct_winner;
    amts(ex);
    space = 1;
    avg_p_correct_winner = avg_p_correct_winner + p_correct_winner;
    avg_weighted_correct_winner = avg_weighted_correct_winner + p_correct_winner*amts(ex);

end

n_not_excluded
novel_count

avg_diff1 = avg_diff_sum1 / n_not_excluded
avg_weighted_diff1 = avg_weighted_diff_sum1 / n_not_excluded

avg_diff2 = avg_diff_sum2 / n_not_excluded
avg_weighted_diff2 = avg_weighted_diff_sum2 / n_not_excluded

avg_p_correct_pocket1 = avg_p_correct_pocket1 / n_not_excluded
avg_p_correct_pocket2 = avg_p_correct_pocket2 / n_not_excluded

avg_p_correct_winner = avg_p_correct_winner / n_not_excluded
avg_weighted_correct_winner = avg_weighted_correct_winner / n_not_excluded
