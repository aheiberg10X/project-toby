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

    training_show = csvread('nodes/show_4-round_perm0_train_merged.csv');
    [show_nex natt] = size(training_show);
    natt
    N
    assert( N+2 == natt );

    show_evidence = cell(N, show_nex);
    show_evidence = num2cell( training_show(:,1:N)' );

    training_noshow = csvread('nodes/noshow_4-round_perm0_train_merged.csv');
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
priors = [[42,42,42,42,42,42,42,42,42,42,42,42];[42,42,42,42,42,42,42,42,42,42,42,42];[0.669306052267,0,0.272381453376,0,0.0368859699055,0.00821651075056,0.00955125210516,0.00133081564474,0.00153102684793,0.000777290553564,1.96285493324e-05,0];[0,0,0.00256741425268,0,0,5.88856479973e-05,3.53313887984e-05,7.85141973297e-06,0,0,0,0.997330517291];[0,0,0.706192022172,0,0.00388252705796,0.224668375659,0.0224550604363,0.0168923295555,0.00628898720611,0.00311701363399,0.0165036842787,0];[0,0,0.0556430116476,1.57028394659e-05,0.000125622715728,0.000718404905567,0.0013582956138,0.000231616882123,9.42170367957e-05,8.24399071962e-05,4.31828085314e-05,0.941687505643];[42,42,42,42,42,42,42,42,42,42,42,42];[42,42,42,42,42,42,42,42,42,42,42,42];[0.996953649144,0,0,0.00286184249267,0.000180582653858,3.92570986649e-06,0,0,0,0,0,0];[0,0,0.174705866188,4.31828085314e-05,0.00270873980788,0.000482862313578,5.10342282643e-05,0,0,0,0,0.822008314653];[0.819425197561,0,0.00258311709215,0.153126239052,0.0220467866102,0.00136222132367,0.000251245431455,0.000286576820254,5.88856479973e-05,0.000141325555194,0.000718404905567,0];[0,0,0.00268518554868,5.49599381308e-05,0.000321908209052,0.000208062622924,3.92570986649e-06,3.92570986649e-06,0,7.85141973297e-06,0,0.996714180842];[42,42,42,42,42,42,42,42,42,42,42,42];[42,42,42,42,42,42,42,42,42,42,42,42];[0.992721733908,0,0,0.00482862313578,0.00233579737056,6.28113578638e-05,4.71085183978e-05,0,0,3.92570986649e-06,0,0];[0,0,0.141329480903,0.000137399845327,0.00238683159882,0.00286184249267,0.000604559319439,0.000157028394659,0.000168805524259,8.24399071962e-05,1.57028394659e-05,0.852255909175];[0.845762785056,0,0.00649312411917,0.0823810215482,0.0592075562064,0.00452241776619,0.000255171141322,0.00118556437968,0.000121697005861,4.31828085314e-05,2.74799690654e-05,0];[0,0,0.0058924905096,3.92570986649e-06,0.000200211203191,0.000263022561055,2.74799690654e-05,1.17771295995e-05,0,1.57028394659e-05,0,0.993585390078];[42,42,42,42,42,42,42,42,42,42,42,42];[42,42,42,42,42,42,42,42,42,42,42,42];[0.901413648123,0,0,0.0676674609686,0.02999242338,0.000478936603711,0.000302279659719,4.31828085314e-05,1.96285493324e-05,4.71085183978e-05,3.53313887984e-05,0];[0,0,0.10937027688,0.000741959164766,0.00311701363399,0.00802022525723,0.00229261456203,0.0007262563253,0.000588856479973,0.000329759628785,0.000490713733311,0.874322324334];[0.787897821624,0,0.0864245027107,0.0663798281324,0.0418205872077,0.0120794092592,0.00109919876262,0.00321908209052,0.00050249086291,0.000380793857049,0.000196285493324,0];[0,0,0.0163073987854,0,0,0,0,0,0,0,0,0.983692601215]];
for i=1:N
    %k = node_sizes(i);
    %ps = parents(dag, i);
    %psz = prod(node_sizes(ps));

    %CPT = sample_dirichlet(p*ones(1,k), psz);
    %bnet.CPD{i} = tabular_CPD(bnet, i, 'CPT', CPT);
    if i == 1 || i == 2 || i == 7 || i == 8 || i == 13 || i == 14 || ...
       i == 19 || i == 20 
        bnet.CPD{i} = root_CPD(bnet, i);
    else 
        if i/6 <= 1
            node_size = preflop_buckets;
        elseif i/6 <= 2
            node_size = flop_buckets;
        elseif i/6 <= 3
            node_size = turn_buckets;
        else  
            node_size = river_buckets;
        end
        CPT = reshape( repmat( priors(i,:), node_size^2, 1 ), 1, active_action_state_size*node_size^2 );
        bnet.CPD{i} = tabular_CPD(bnet, i, CPT);
    end
end
dirichlet_done = 1

s=struct(bnet.CPD{3});  % violate object privacy
s.CPT(1,1,11)
s.CPT(1,1,12)
s.CPT(9,10,11)
s.CPT(9,10,10)

%training_cells = num2cell(training');
%for i=1:nexps
%    for c=find(training(i,[12 13 14 15]) == 8)
%        training_cells{11+c,i} = [];
%    end
%end
%masking_dummy_moves = 1

assert(false);

if em == 0
    bnet_learned = learn_params(bnet, evidence);
elseif em == 1
    engine = jtree_inf_engine(bnet);
    [bnet_learned LL] = learn_params_em( engine, evidence, 10 );
end
learn_params = 1

engine_built = 1
