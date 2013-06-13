seed = 42;
randn('state',seed);
N = 12;

training = csvread('../../project-toby/nodes/hugh_SartreNL/perm1/training_4-rounds_showdown.csv') %show_4-round_perm0_train_merged_scaled.csv');

dag = zeros(N,N);

%big aggregate action states
dag( [1 2], 3 ) = 1;
dag( [4 5], 6 ) = 1;
dag( [7 8], 9 ) = 1;
dag( [10 11], 12 ) = 1;

num_act_bet_ratios = 8;
agg_action_size = 1315; 
preflop_buckets = 10;
flop_buckets = 20;
turn_buckets = 15;
river_buckets = 10;

node_sizes = [ preflop_buckets, preflop_buckets, agg_action_size, ...
               flop_buckets, flop_buckets, agg_action_size, ...
               turn_buckets, turn_buckets, agg_action_size, ...
               river_buckets, river_buckets, agg_action_size ];

observed_nodes = 1:12;
discrete_nodes = 1:12;

bnet = mk_bnet( dag, node_sizes, 'observed', observed_nodes, 'discrete', discrete_nodes );

for i=1:N
    if i == 1 || i == 2 || i == 4 || i == 5 || i == 7 || i == 8 || ...
       i == 10 || i == 11 
        bnet.CPD{i} = root_CPD(bnet, i);
    else 

        %if i == 3
        %    node_size = preflop_buckets;
        %elseif i == 6
        %    node_size = flop_buckets;
        %elseif i == 9
        %    node_size = turn_buckets;
        %else  
        %    node_size = river_buckets;
        %end
        %CPT = reshape( repmat( priors(i,:), node_size^2, 1 ), 1, active_action_state_size*node_size^2 );
        bnet.CPD{i} = tabular_CPD(bnet, i);
    end


    bnet_learned = learn_params(bnet, evidence);


