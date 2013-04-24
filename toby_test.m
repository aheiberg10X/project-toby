%for testing river belief buckets ONLY
%test = csvread('../../project-toby/nodes/noshow_4-round_small.csv');
%test = csvread('../../project-toby/nodes/show_test_small.csv');
test = csvread('../../project-toby/nodes/test_4-rounds_showdown.csv');
test = test(1:10000,1:N);
%amts = test(1:10000,N+1);
[ncases,natt] = size(test);

%shit, we printed all -1, but we want the true label for testing
%should reparse, printing everything, and use a hand-input visible mask
%visible_ixs = find( test(0,:) >= 0 );
visible_ixs = [3 6 9 12 13 14 15];

%if we want to get accuracy doing no prediction
%can do this faster by jumping over engine inteference
computing_baseline = 0;

%we want to be able to exclude arbitrary types of hands from evaluation
%for examples, it is easy to get good accuacy by predicting check every time
%what is our prediction rate for the hands that do not have all checks?
focus_nodes = [12 13 14 15];
special_focus_values = [1 8 1 8]; %; [1 3 5 8]; [1 3 4 8]];
%can ignore focus, and include all else
%or include all else, and ignore focus
ignore_special_focus = 1;
n_not_excluded = 0;

engine = jtree_inf_engine(bnet_learned);

%s=struct(bnet_learned.CPD{10});  % violate object privacy
%s.CPT

%for each test hand, we will get a distribution over buckets
%we will sample this dist k times, and compute the average difference
%between this sample and the true label
%add this average difference for each hand to avg_distance_sum
avg_diff_sum = 0

%which node are we trying to predict?
predict_node = 10;  %or 11
n_river_buckets = 10;
%difference between midway of percentile 1 and percentile 2, percentile2
%and percentile 3, etc
%distance between a and b is:
%sum(distances(a,b-1))
distances = [0.2889 0.1879 0.1223 0.0798 0.0522 0.0346 0.0234 0.0167 0.0131];


%count how many test examples were not seen when training
%the marginal distribution for these examples is set to all 0's
novel_count = 0;

n_test_rows = size(test,1)

s=struct(bnet_learned.CPD{10});  % violate object privacy
prior10 = s.CPT;

for i=1:n_test_rows
    if mod(i,1000) == 0
        i
    end

    %do not evaluate the rows where the specified nodes take on 
    %specifics values
    focus_values = test(i,focus_nodes);
    in_focus = sum(ismember( special_focus_values, focus_values, 'rows' ));
    should_ignore = ~xor(in_focus,ignore_special_focus);
    if( should_ignore )
        continue;
    end

    n_not_excluded = n_not_excluded + 1;

    %turn the data into a cell array evidence, turning all values not
    %marked as visible into []
    evidence = cell(1,N);
    evidence( :,visible_ixs ) = num2cell( test(i,visible_ixs) );

    %get rid of the dummy values as well
%    active_values = test(i,[12 13 14 15]);
%    dummy_ix_offsets = find(active_values == 8);
%    for ix=dummy_ix_offsets 
%        evidence{11+ix} = [];
%    end
    
    true_label = test(i,predict_node);
    
    n_samples = 100;
    marginal = zeros(1,n_river_buckets);
    if( ~computing_baseline )
        %get the distribution over the outcomes of predict_node
        [engine2, ll] = enter_evidence(engine, evidence);
        marg = marginal_nodes(engine2, predict_node);
        evidence
        marginal = marg.T
       % meen = mean(marginal .* 1:n_river_buckets);
       % sigma = std(marginal .* 1:n_river_buckets);
       % samples = round(normrnd(meen,sigma,1,n_samples));
        %bound
        %predicted_buckets = samples(samples >= 1 & samples <= n_river_buckets);
        predicted_buckets = discretesample( marginal, n_samples );

        %test to factor out priors.  helped a little on hands not 1818
    %    marginal = marginal ./ prior10;
    %    marginal = marginal / sum(marginal);

        true_label
        %test(i,:)
    end

    %if this instance wasn't in training, it will be all zeros
    %use a uniform prior instead
    if (sum(marginal) < .99 | computing_baseline )
        evidence;
        marginal = ones(1,n_river_buckets) / n_river_buckets;
        %marginal = prior10(evidence{6}, evidence{9}, :);
        novel_count = novel_count + 1;
        predicted_buckets = discretesample( marginal, n_samples );
    end

    diff_sum = 0;
    for i=1:size(predicted_buckets,2)
        %diff_sum = diff_sum + abs(true_label - predicted_buckets(i));
        if(true_label == predicted_buckets(i))
            diff = 0;
        elseif (true_label > predicted_buckets(i))
            a = predicted_buckets(i);
            b = true_label;
            diff = sum(distances(a:b-1));
        else
            a = true_label;
            b = predicted_buckets(i);
            diff = sum(distances(a:b-1));
        end
        diff_sum = diff_sum + diff;
    end
    avg_diff = diff_sum / n_samples;
    avg_diff_sum = avg_diff_sum + avg_diff; %*amts(i);

end
%fclose(fout_dist);
%fclose(fout_label);

%avg_chance_of_correct_prediction = running_sum / n_test_rows
n_not_excluded
overall_avg_diff = (avg_diff_sum / n_not_excluded) / mean(distances)
novel_count

