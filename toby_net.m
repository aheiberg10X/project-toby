scaling = 1 
if scaling == 1
    training = csvread('../../project-toby/nodes/show_4-round_perm0_train_merged_scaled.csv');
elseif scaling == 0
    training = csvread('../../project-toby/nodes/show_4-round_perm0_train_merged.csv');
else
    training = [1 1 1 1 1 1 1 1 1 2 1 5 3 3 3;
                1 1 1 1 1 1 1 1 1 2 1 3 3 3 3;
                1 1 1 1 1 1 1 1 1 2 1 3 3 3 3;
                1 1 1 1 1 1 1 1 1 4 1 3 3 3 3;
                1 1 1 1 1 1 1 1 1 4 1 3 3 3 3;
                1 1 1 1 1 1 1 1 1 2 1 3 3 3 3 ]
end
%training = csvread('../../project-toby/nodes/training_4-rounds_showdown.csv');
data_inputted = 1

seed = 42;
rand('state',seed);
randn('state',seed);
dag_switch = 4;
N = 15;
training = training(:,1:N);
[nexps, natts] = size(training);
%encode the graph
dag = zeros(N,N);

%1 = baseline.  Streets not connected
if( dag_switch == 1 )
    dag(10,[12 13]) = 1;
    dag(11,[14 15]) = 1;
    dag(12,[13 14 15]) = 1;
    dag(13, 15) = 1;
    dag(14,[13 15]) = 1;
%2 = action 2 action : past actions connected to each active
%runs out of memory on laptop
elseif( dag_switch == 2 )
    dag([6 9],[12 13 14 15]) = 1;
    dag(10,[12 14]) = 1;
    dag(11,[13,15]) = 1;
    dag(12,[13 14 15]) = 1;
    dag(13,[14 15]) = 1;
    dag(14,15) = 1;
%3 = past 2 belief : past actions connect to current belief
elseif( dag_switch == 3 )
    dag([6 9],[10 11]) = 1;
    dag(10,[12 13]) = 1;
    dag(11,[14 15]) = 1;
    dag(12,[13 14 15]) = 1;
    dag(13,15) = 1;
    dag(14,[13 15]) = 1;
elseif( dag_switch == 4 );
    dag([6 9],[10 11]) = 1;
    dag(12,[13 14 15]) = 1;
    dag(13,15) = 1;
    dag(14,[13 15]) = 1;
    dag([12 13],10 ) = 1;
    dag([14 15],11 ) = 1;

%4 = connected by belief transitions
else
    dag([1 2],3) = 1;
    dag(1,4) = 1;
    dag(2,5) = 1;

    dag([4 5],6) = 1;
    dag(4,7) = 1;
    dag(5,8) = 1;
    
    dag([7 8],9) = 1;
    dag(7,10) = 1;
    dag(8,11) = 1;

    %TODO incorporate board edges into the graph, fix CPT of belief nodes

    dag(10,[12 14]) = 1;
    dag(11,[13,15]) = 1;
    
    dag(12,[13 14 15]) = 1;
    dag(13,[14 15]) = 1;
    dag(14,15) = 1;
end


num_past_bet_ratios = 8; 
num_act_bet_ratios = 8;
past_action_state_size = 56; %num_past_bet_ratios*2*2*2*2;
active_action_state_size = num_act_bet_ratios + 3 + 1; %+3 for k,f,c + dummy
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
names = {'b11','b21','a1','b12','b22','a2','b13','b23','a3','b14','b24','a141','a142','a241','a242'};

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
%TODO, we know everything except 14,15 is always observed
%does giving this hint speed things up?
%observed_nodes = 1:N;

bnet = mk_bnet( dag, node_sizes, 'names', names ); % 'observed', observed_nodes );
bnet_made = 1

%hard code belief transistions across street.  Will eventually derive these
%parameters experimentally.

%If p = 1, each entry is drawn from U[0,1]
%If p << 1, this encourages "deterministic" CPTs (one entry near 1, the rest near 0)
% If p >> 1, the entries will all be near 1/k, k is arity of node
p = 1
for i=1:N
    %k = node_sizes(i);
    %ps = parents(dag, i);
    %psz = prod(node_sizes(ps));

    %CPT = sample_dirichlet(p*ones(1,k), psz);
    %bnet.CPD{i} = tabular_CPD(bnet, i, 'CPT', CPT);
    bnet.CPD{i} = tabular_CPD(bnet, i);
end
dirichlet_done = 1

%s=struct(bnet.CPD{10});  % violate object privacy
%s.CPT

%training_cells = num2cell(training');
%for i=1:nexps
%    for c=find(training(i,[12 13 14 15]) == 8)
%        training_cells{11+c,i} = [];
%    end
%end
%masking_dummy_moves = 1

%assuming training.csv has been loaded

bnet_learned = learn_params(bnet, training');

%engine = jtree_inf_engine(bnet);
%[bnet_learned LL]= learn_params_em( engine, training_cells, 10 );
learn_params = 1

%engine2 = jtree_inf_engine(bnet);
%max_iter = 1
%[bnet3, LLtrace] = learn_params_em(engine2, num2cell(training'), max_iter);
%plot(LLtrace, 'x-')

engine_built = 1



