%for testing river belief buckets ONLY
%test = csvread('../../project-toby/nodes/noshow_4-round_small.csv');
test = csvread('../../project-toby/nodes/show_test_small.csv');
[ncases,natt] = size(test);

%shit, we printed all -1, but we want the true label for testing
%should reparse, printing everything, and use a hand-input visible mask
%visible_ixs = find( test(0,:) >= 0 );
visible_ixs = [12 13 14 15];

%if we want to get accuracy doing no prediction
%can do this faster by jumping over engine inteference
computing_baseline = 0;

%we want to be able to exclude arbitrary types of hands from evaluation
%for examples, it is easy to get good accuacy by predicting check every time
%what is our prediction rate for the hands that do not have all checks?
focus_nodes = [10];
%ignore_values = [];
special_focus_values = [10];
%can ignore focus, and include all else
%or include all else, and ignore focus
ignore_special_focus = 0;
n_not_excluded = 0;

engine = jtree_inf_engine(bnet_learned);
s=struct(bnet_learned.CPD{10});  % violate object privacy
s.CPT

%for each test hand, we will get a distribution over buckets
%we will sample this dist k times, and compute the average difference
%between this sample and the true label
%add this average difference for each hand to avg_distance_sum
avg_diff_sum = 0

%which node are we trying to predict?
predict_node = 10;  %or 11
n_river_buckets = 10;

%count how many test examples were not seen when training
%the marginal distribution for these examples is set to all 0's
novel_count = 0;

n_test_rows = size(test,1)

%[dist_filename err] = sprintf('node_%d_distribution.csv', predict_node );
%[label_filename err] = sprintf('node_%d_labels.csv', predict_node );
%fout_dist = fopen(dist_filename, 'wt');
%fout_label = fopen( label_filename, 'wt');
for i=1:n_test_rows
    if mod(i,1000) == 0
        i
    end

    %do not evaluate the rows where the specified nodes take on 
    %specifics values
    focus_values = test(i,focus_nodes);
    in_focus = ismember( special_focus_values, focus_values, 'rows' );
    should_ignore = ~xor(in_focus,ignore_special_focus);
    if( should_ignore )
        continue;
    end

    n_not_excluded = n_not_excluded + 1;
    test(i,:)

    %turn the data into a cell array evidence, turning all values not
    %marked as visible into []
    evidence = cell(1,N);
    evidence( :,visible_ixs ) = num2cell( test(i,visible_ixs) );
    
%    focus_values
    true_label = test(i,predict_node);
    label12 = test(i,12)

    %s=struct(bnet3.CPD{i});  % violate object privacy
    %CPT3{i}=s.CPT;

    %get the distribution over the outcomes of predict_node
    [engine2, ll] = enter_evidence(engine, evidence);
    marg = marginal_nodes(engine2, predict_node);
    marginal = marg.T;
    %true_label
    %test(i,:)

    %if this instance wasn't in training, it will be all zeros
    %use a uniform prior instead
    if (sum(marginal) < .99 | computing_baseline )
        marginal = ones(1,n_river_buckets) / n_river_buckets;
        novel_count = novel_count + 1;
    end
    %fprintf( fout_dist, '%f,%f,%f,%f,%f,%f,%f,%f,%f,%f\n', marginal);
    %fprintf( fout_label, '%d\n', true_label );

    %will be sampling from the dist in python instead
    %gives better control on what kind of hands I want to evaluate
    n_samples = 100;
    predicted_buckets = discretesample( marginal, n_samples );
    diff_sum = 0;
    for i=1:n_samples
        diff_sum = diff_sum + abs(true_label - predicted_buckets(i));
    end
    avg_diff = diff_sum / n_samples;
    avg_diff_sum = avg_diff_sum + avg_diff;

end
%fclose(fout_dist);
%fclose(fout_label);

%avg_chance_of_correct_prediction = running_sum / n_test_rows
n_not_excluded
overall_avg_diff = avg_diff_sum / n_not_excluded
novel_count

