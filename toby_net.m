seed = 42;
rand('state',seed);
randn('state',seed);


%currently only for river
use_texture = false;
if use_texture
    N = 18+3;
    %encode the graph
    dag = zeros(N,N);
    %preflop belief nodes for player 1 and 2
    dag(1,[5 3]) = 1;
    dag(2,[4 6]) = 1;
    %preflop action nodes
    dag([3 4],[7 8]) = 1;
    %flop belief nodes 
    dag(5,[7 9]) = 1;
    dag(6,[8 10]) = 1;
    %flop action nodes
    dag([7 8],[11 12]) = 1;  %consider making parents of 15,16 too
    %turn belief nodes
    dag(9, [11 13]) = 1;
    dag(10, [12 14]) = 1;
    %turn action nodes
    dag([11 12], [15 16]) = 1;
    %river belief nodes
    dag(13,15) = 1;
    dag(14,16) = 1;
else
    N = 18;
    %encode the graph
    dag = zeros(N,N);
    %preflop belief nodes for player 1 and 2
    dag(1,[3]) = 1;
    dag(2,[4]) = 1;
    %preflop action nodes
    dag([3 4],[15 16 17 18]) = 1;
    %flop belief nodes 
    dag(5,[7]) = 1;
    dag(6,[8]) = 1;
    %flop action nodes
    dag([7 8],[15 16 17 18]) = 1;  
    %turn belief nodes
    dag(9, [11]) = 1;
    dag(10, [12]) = 1;
    %turn action nodes
    dag([11 12], [15 16 17 18]) = 1;
    %river belief nodes
    dag(13,[15 17]) = 1;
    dag(14,[16 18]) = 1;
end



summarized_action_state_size = 7*2*2+1;  %+1 for fold
active_action_state_size = ;
preflop_buckets = 10;
flop_buckets = 20;
turn_buckets = 15;
river_buckets = 10;

node_sizes = [preflop_buckets,   preflop_buckets, ...
              action_state_size, action_state_size, ...
              flop_buckets,      flop_buckets, ...
              action_state_size, action_state_size, ...
              turn_buckets,      turn_buckets, ...
              action_state_size, action_state_size, ...
              river_buckets,     river_buckets, ...
              action_state_size, action_state_size];
          
names = {'b11','b12','a11','a12','b21','b22','a21','a22','b31','b32','a31','a32','b41','b42','a41','a42'};
%NOTE
%This will change for each street
%To start we are doing fully observed for four rounds
observed_nodes = 1:16;

bnet = mk_bnet( dag, node_sizes, 'names', names, 'observed', observed_nodes );

%hard code belief transistions across street.  Will eventually derive these
%parameters experimentally.

%uniform for now, clamp them how?
%this is done automatically
%flop_bucket_CPT = ones(preflop_buckets, flop_buckets) .* 1/flop_buckets;
%turn_bucket_CPT = ones(flop_buckets, turn_buckets) .* 1/turn_buckets;
%river_bucket_CPT = ones(turn_buckets, river_buckets) .* 1/river_buckets;

%If p = 1, each entry is drawn from U[0,1]
%If p << 1, this encourages "deterministic" CPTs (one entry near 1, the rest near 0)
% If p >> 1, the entries will all be near 1/k, k is arity of node
p = 1
for i=1:N
    k = node_sizes(i);
    ps = parents(dag, i);
    psz = prod(node_sizes(ps));
    CPT = sample_dirichlet(p*ones(1,k), psz);
    bnet.CPD{i} = tabular_CPD(bnet, i, 'CPT', CPT);
end

%assuming training.csv has been loaded
bnet2 = learn_params(bnet, training');

engine = jtree_inf_engine(bnet2);


%assuming test.csv has been loaded

%compute the probability the second player's true bucket would have 
%been randomly sampled given the evidence, for each game
%average these probabilities
running_sum = 0;
%which node are we trying to predict?
predict_node = 6;
for i=1:size(test,1)
    evidence = num2cell(test(i,1:16));
    evidence{predict_node} = [];
    %evidence{end+1} = []
    [engine2, ll] = enter_evidence(engine, evidence);
    marg = marginal_nodes(engine2, predict_node);
    marg.T
    prob_correct = marg.T(test(i,predict_node))
    running_sum = running_sum + prob_correct;
end

avg_chance_of_correct_prediction = running_sum / size(test,1)

