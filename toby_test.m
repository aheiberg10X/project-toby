%for testing river belief buckets ONLY
%test = csvread('noshow_4-round_small.csv');
test = csvread('show_test_small.csv');
[ncases,natt] = size(test);
%shit, we printed all -1, but we want the true label for testing
%should reparse, printing everything, and use a hand-input visible mask
%visible_ixs = find( test(0,:) >= 0 );
visible_ixs = [3 6 9 12 13 14 15];

%assuming test.csv has been loaded
engine = jtree_inf_engine(bnet2);

%for each test hand, we will get a distribution over buckets
%we will sample this dist k times, and compute the average difference
%between this sample and the true label
%add this average difference for each hand to avg_distance_sum
avg_distance_sum = 0

%which node are we trying to predict?
predict_node = 10;  %or 11
n_river_buckets = 10;
novel_count = 0;

n_test_rows = size(test,1)
%avg_diffs = zeros(1:n_test_rows)
%margs = zeros(1:n_test_rows)

[dist_filename err] = sprintf('node_%d_distribution.csv', predict_node );
[label_filename err] = sprintf('node_%d_labels.csv', predict_node );
fout_dist = fopen(dist_filename, 'wt');
fout_label = fopen( label_filename, 'wt');
for i=1:n_test_rows
    if mod(i,1000) == 0
        i
    end
    evidence = cell(1,N);
    evidence( :,visible_ixs ) = num2cell( test(i,visible_ixs) );
%    num2cell(test(i,1:N));
%    evidence{predict_node} = [];
%    cases( :,visible_ixs ) = num2cell( test(:,visible_ixs) );

    true_label = test(i,predict_node);
    %evidence{end+1} = []
    [engine2, ll] = enter_evidence(engine, evidence);
    marg = marginal_nodes(engine2, predict_node);
    marginal = marg.T;
    %if (sum(marginal) > .99 && sum(marginal) < 1.01)
    %    prob_correct = marg.T(test(i,true_label));
    %    running_sum = running_sum + prob_correct;
    %else 
    %if this instance wasn't in training, use a uniform prior
    %otherwise everything is set to 0 and that's not right
    if (sum(marginal) < .99 )
        %uniform
        marginal = ones(1,n_river_buckets) / n_river_buckets;
        novel_count = novel_count + 1;
    end
    fprintf( fout_dist, '%f,%f,%f,%f,%f,%f,%f,%f,%f,%f\n', marginal);
    fprintf( fout_label, '%d\n', true_label );

    %will be sampling from the dist in python instead
    %gives better control on what kind of hands I want to evaluate
%    n_samples = 100;
%    predicted_buckets = discretesample( marginal, n_samples );
%    diff_sum = 0
%    for i=1:n_samples
%        diff_sum = diff_sum + abs(true_bucket - predicted_buckets(i));
%    end
%    avg_diff = diff_sum / n_samples;
    %avg_diff_sum = avg_diff_sum + avg_diff;

end
fclose(fout_dist);
fclose(fout_label);

%avg_chance_of_correct_prediction = running_sum / n_test_rows
%overall_avg_diff = avg_diff_sum / n_test_rows
novel_count

