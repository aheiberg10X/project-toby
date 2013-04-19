%for testing river belief buckets ONLY

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

avg_diffs = zeros(1:size(test,1))
margs = zeros(1:size(test,1))
for i=1:size(test,1)
    evidence = num2cell(test(i,1:N));
    evidence{predict_node} = [];
    true_bucket = test(i,predict_node);
    %evidence{end+1} = []
    [engine2, ll] = enter_evidence(engine, evidence);
    marg = marginal_nodes(engine2, predict_node);
    marginal = marg.T;
    margs(i) = marginal;
    %if (sum(marginal) > .99 && sum(marginal) < 1.01)
    %    prob_correct = marg.T(test(i,true_label));
    %    running_sum = running_sum + prob_correct;
    %else 
    %if this instance wasn't in training, use a uniform prior
    %otherwise everything is set to 0 and that's not right
    if (sum(marginal) < .99 && sum(marginal) > 1.01)
        %uniform
        marginal = ones(1,n_river_buckets) / n_river_buckets;
        novel_count = novel_count + 1;
    end
    n_samples = 100;
    predicted_buckets = discretesample( marginal, n_samples );
    diff_sum = 0
    for i=1:n_samples
        diff_sum = diff_sum + abs(true_bucket - predicted_buckets(i));
    end
    avg_diff = diff_sum / n_samples;
    %avg_diff_sum = avg_diff_sum + avg_diff;

end

csvwrite('belief_distributions.csv',margs)

%avg_chance_of_correct_prediction = running_sum / size(test,1)
%overall_avg_diff = avg_diff_sum / size(test,1)
novel_count

