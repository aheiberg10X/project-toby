scaling = 0
dag_switch = 10
em = 1 

seed = 42;
rand('state',seed);
randn('state',seed);
N = 24;

if em == 0
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

    evidence = training';

elseif em == 1

    training_show = csvread('../../project-toby/nodes/show_4-round_perm0_train_merged.csv');
    [show_nex natt] = size(training_show);
    natt
    N
    assert( N+2 == natt );

    show_evidence = cell(N, show_nex);
    show_evidence = num2cell( training_show(:,1:N)' );

    training_noshow = csvread('../../project-toby/nodes/noshow_4-round_perm0_train_merged.csv');
    [noshow_nex natt] = size(training_noshow);
    assert( N+2 == natt );

    %mask
    visible_ixs = [3 4 5 6 9 10 11 12 15 16 17 18 21 22 23 24];
    noshow_evidence = cell( N, noshow_nex );
    noshow_evidence( visible_ixs,: ) = num2cell( training_noshow(:,visible_ixs)' );
    
    size(show_evidence)
    size(noshow_evidence)
    evidence = [show_evidence, noshow_evidence];

    %mix em up?

end
data_inputted = 1

%encode the graph
dag = zeros(N,N);

%1,2,3,4 deprecated, using past action nodes
%1 = baseline. Beliefs influence actions.  Streets not connected
if( dag_switch == 1 )
    dag(10,[12 13]) = 1;
    dag(11,[14 15]) = 1;
    dag(12,[13 14 15]) = 1;
    dag(13, 15) = 1;
    dag(14,[13 15]) = 1;
%2 = baseline.  Actions influence beliefs.  Streets not connected
elseif( dag_switch == 2 )
    dag([12 13], 10) = 1;
    dag([14 15], 11) = 1;
    dag(12,[13 14 15]) = 1;
    dag(13, 15) = 1;
    dag(14,[13 15]) = 1;
%3 = past -> belief -> active
elseif( dag_switch == 3 )
    dag([6 9],[10 11]) = 1;
    dag(10,[12 13]) = 1;
    dag(11,[14 15]) = 1;
    dag(12,[13 14 15]) = 1;
    dag(13,15) = 1;
    dag(14,[13 15]) = 1;
%4 = past -> belief, active -> belief
elseif( dag_switch == 4 );
    dag([6 9],[10 11]) = 1;
    dag([12 13], 10) = 1;
    dag([14 15], 11) = 1;
    dag(12,[13 14 15]) = 1;
    dag(13,15) = 1;
    dag(14,[13 15]) = 1;
%}
%streets not connected, no inter-action, both beliefs influence every action
elseif( dag_switch == 10 )
    dag( [1 2], [3 4 5 6] ) = 1;
    dag( [7 8], [9 10 11 12]) = 1;
    dag( [13 14], [15 16 17 18] ) = 1;
    dag( [19 20], [21 22 23 24] ) = 1;
%reverse directionality from #10
elseif( dag_switch == 11 )
    dag( [3 4 5 6], [1 2] ) = 1;
    dag( [9 10 11 12], [7 8] ) = 1;
    dag( [15 16 17 18], [13 14] ) = 1;
    dag( [21 22 23 24], [19 20] ) = 1;
%streets not connected, inter-action, beliefs influence every a
elseif( dag_switch == 12 )
    dag( [10 11], [12 13 14 15] ) = 1;
    dag(12,[13 14 15]) = 1;
    dag(13,15) = 1;
    dag(14,[13 15]) = 1;

%5 = connected by belief transitions
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


%num_past_bet_ratios = 8; 
num_act_bet_ratios = 8;
%past_action_state_size = 56; %num_past_bet_ratios*2*2*2*2;
active_action_state_size = num_act_bet_ratios + 3 + 1; %+3 for k,f,c + dummy
preflop_buckets = 10;
flop_buckets = 20;
turn_buckets = 15;
river_buckets = 10;

node_sizes = [preflop_buckets,        preflop_buckets, ...
              active_action_state_size, active_action_state_size, ...
              active_action_state_size, active_action_state_size, ...
              flop_buckets,           flop_buckets, ...
              active_action_state_size, active_action_state_size, ...
              active_action_state_size, active_action_state_size, ...
              turn_buckets,           turn_buckets, ...
              active_action_state_size, active_action_state_size, ...
              active_action_state_size, active_action_state_size, ...
              river_buckets,          river_buckets, ...
              active_action_state_size, active_action_state_size, ...
              active_action_state_size, active_action_state_size];

observed_nodes = [3 4 5 6 9 10 11 12 15 16 17 18 21 22 23 24];
discrete_nodes = 1:N;

bnet = mk_bnet( dag, node_sizes, 'observed', observed_nodes, 'discrete', discrete_nodes );
bnet_made = 1

%If p = 1, each entry is drawn from U[0,1]
%If p << 1, this encourages "deterministic" CPTs (one entry near 1, the rest near 0)
% If p >> 1, the entries will all be near 1/k, k is arity of node
%p = 1
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

if em == 0
    bnet_learned = learn_params(bnet, evidence);
elseif em == 1
    engine = jtree_inf_engine(bnet);
    [bnet_learned LL] = learn_params_em( engine, evidence, 10 );
end
learn_params = 1

engine_built = 1
