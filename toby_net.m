seed = 42;
rand('state',seed);
randn('state',seed);


%currently only for river
use_texture = false;
use_merged = true;
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
elseif use_merged
    N = 15;
    %encode the graph
    dag = zeros(N,N);

    %preflop belief nodes for player 1 and 2
    dag([1 2],3) = 1;

    %preflop action nodes
    %consider not connecting preflop to river nodes, probably not useful and
    %blows up CPTs
    %dag([3 4],[15 16 17 18]) = 1;

    %flop belief nodes 
    dag([4 5],6) = 1;

    %flop action nodes
    dag(6,[12 13 14 15]) = 1;  

    %turn belief nodes
    dag([7 8], 9) = 1;

    %turn action nodes
    dag(9, [12 13 14 15]) = 1;

    %river belief nodes
    dag(10,[12 14]) = 1;
    dag(11,[13 15]) = 1;

    %river action nodes
    dag(12, [13 14 15]) = 1;
    dag(13, [14 15]) = 1;
    dag(14, 15) = 1;
else
    N = 18;
    %encode the graph
    dag = zeros(N,N);

    %preflop belief nodes for player 1 and 2
    dag(1,[3]) = 1;
    dag(2,[4]) = 1;

    %preflop action nodes
    %consider not connecting preflop to river nodes, probably not useful and
    %blows up CPTs
    %dag([3 4],[15 16 17 18]) = 1;

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


num_bet_ratios = 4 
past_action_state_size = num_bet_ratios*2*2*2*2;
active_action_state_size = num_bet_ratios + 3 ; %+3 for k,f,c
preflop_buckets = 10;
flop_buckets = 20;
turn_buckets = 15;
river_buckets = 10;

node_sizes = [preflop_buckets,        preflop_buckets, ...
              past_action_state_size, ...
              flop_buckets,           flop_buckets, ...
              past_action_state_size, ...
              turn_buckets,           turn_buckets, ...
              past_action_state_size, ...
              river_buckets,          river_buckets, ...
              active_action_state_size, active_action_state_size, ...
              active_action_state_size, active_action_state_size];
names = {'b11','b12','a1','b21','b22','a2','b31','b32','a3','b41','b42','a411','a412','a421','a422'};
%{
node_sizes = [preflop_buckets,        preflop_buckets, ...
              past_action_state_size, past_action_state_size, ...
              flop_buckets,           flop_buckets, ...
              past_action_state_size, past_action_state_size, ...
              turn_buckets,           turn_buckets, ...
              past_action_state_size, past_action_state_size, ...
              river_buckets,          river_buckets, ...
              active_action_state_size, active_action_state_size, ...
              active_action_state_size, active_action_state_size];
              
names = {'b11','b12','a11','a12','b21','b22','a21','a22','b31','b32','a31','a32','b41','b42','a411','a412','a421','a422'};
%}  


%NOTE
%This will change for each street
%To start we are doing fully observed for four rounds
observed_nodes = 1:N;

bnet = mk_bnet( dag, node_sizes, 'names', names, 'observed', observed_nodes );
bnet_made = 1

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
    %bnet.CPD{i} = tabular_CPD(bnet, i);
end
dirichlet_done = 1

%assuming training.csv has been loaded
bnet2 = learn_params(bnet, training');
learn_params = 1

%engine2 = jtree_inf_engine(bnet);
%max_iter = 1
%[bnet3, LLtrace] = learn_params_em(engine2, num2cell(training'), max_iter);
%plot(LLtrace, 'x-')

engine_built = 1


%assuming test.csv has been loaded
engine = jtree_inf_engine(bnet2);

%compute the probability the second player's true bucket would have 
%been randomly sampled given the evidence, for each game
%average these probabilities
running_sum = 0;
%which node are we trying to predict?
predict_node = 13;
novel_count = 0;
for i=1:size(test,1)
    evidence = num2cell(test(i,1:N))
    evidence{predict_node} = [];
    %evidence{end+1} = []
    [engine2, ll] = enter_evidence(engine, evidence);
    marg = marginal_nodes(engine2, predict_node);
    marginal = marg.T
    if (sum(marginal) > .99 && sum(marginal) < 1.01)
        prob_correct = marg.T(test(i,predict_node));
        running_sum = running_sum + prob_correct;
    %if this instance wasn't in training, use a uniform prior
    %otherwise everything is set to 0 and that's not right
    else
        novel_count = novel_count + 1;
    end
end

avg_chance_of_correct_prediction = running_sum / size(test,1)
novel_count

