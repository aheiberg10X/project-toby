engine = jtree_inf_engine(bnet_learned);

dist = P10gactive( bnet_learned, engine, 3, 3, 3, 3);
assert(False);
%compute P(b|6,9,12,13,14,15)

true_label = 7; 

s=struct(bnet_learned.CPD{10});
prior10 = s.CPT;

z = zeros(1,10);

value6 = 20;
value9 = 20;
value12 = 1;
value13 = 3;
value14 = 4;
value15 = 12;

%bg69 = reshape( prior10( value6, value9, : ), 10, 1 )

evidence = cell(1,N);
[engine2, ll] = enter_evidence( engine, evidence )
marg = marginal_nodes( engine2, 10);
marginalB = marg.T

s=struct(bnet_learned.CPD{10});
prior10 = s.CPT

evidence = cell(1,N);
evidence{10} = 4;
[engine2, ll] = enter_evidence( engine, evidence );
marg = marginal_nodes( engine2, 12);
marginal12 = marg.T

s = struct(bnet_learned.CPD{12});
reshape(s.CPT(4,:),12,1)


assert(false);

%%marginalB = [0.37518401765, 0.276201169076, 0.161064024402, 0.0736070599966, 0.0369213012943, 0.0299178348925, 0.0183409164962, 0.0126211572208,  0.00805163093616, 0.00809088803483];
%bucket = 2;
%evidence4 = cell(1,N);
%evidence4{10} = bucket;
%evidence4{12} = value12;
%evidence4{14} = value14;
%[engine2, ll] = enter_evidence(engine, evidence4);
%marg = marginal_nodes(engine2, 13);
%marginal = marg.T

s=struct(bnet_learned.CPD{13});
prior13 = reshape(s.CPT(1,value12,value14,:), 12, 1)
lookup13 = prior13(value13);


for bucket=1:10
    bucket
    elems = zeros(1,5);
    
    %compute P_b_given_active = P(b|12,13,14,15)


    evidence = cell(1,N);
    evidence{10} = bucket;
    evidence{12} = value12;
    %evidence{14} = value14;
    [engine2, ll] = enter_evidence(engine, evidence);
    marg13 = marginal_nodes(engine2, 13);
    marginal13 = marg13.T

    A = marginal13(value13)
    assert(false);
    elems(1) = A;

    evidence = cell(1,N);
    evidence{12} = value12;
    %evidence{14} = value14;
    [engine2, ll] = enter_evidence(engine, evidence);
    marg13b = marginal_nodes(engine2, 13);
    marginal13b = marg13b.T;
    B = marginal13b(value13);
    elems(2) = B;
    
    evidence4 = cell(1,N);
    evidence4{10} = bucket;
    [engine2, ll] = enter_evidence(engine, evidence4);
    marg12 = marginal_nodes(engine2, 12);
    marginal12 = marg12.T;
    C = marginal12(value12);
    elems(3) = C;
 
    evidence = cell(1,N);
    [engine2, ll] = enter_evidence(engine, evidence);
    marg10 = marginal_nodes(engine2, 10);
    marginal10 = marg10.T;
    D = marginal10(bucket);
    %D = marginalB(bucket)
    elems(4) = D;

    elems   
    z(bucket) = A*C*D/B;
    
end
z
sum(z)
%Pbgactive = z ./ sum(z)

%evidence = cell(1,N);
%evidence{12} = value12;
%evidence{13} = value13;
%evidence{14} = value14;
%evidence{15} = value15;
%[engine2, ll] = enter_evidence(engine, evidence);
%marg = marginal_nodes(engine2, 10);
%bnt_Pbgactive = marg.T

evidence = cell(1,N);
evidence{12} = value12;
evidence{13} = value13;
[engine2, ll] = enter_evidence(engine, evidence);
marg = marginal_nodes(engine2, 10);
bnt_Pbgactive = marg.T


assert(false);

%compute P(6,9|b) = P(6|b)*P(9|b)
%P6gb
evidence = cell(1,N);
evidence{10} = bucket;
[engine2, ll] = enter_evidence( engine, evidence );
marg6 = marginal_nodes( engine2, 6 );
marginal6 = marg6.T;
P6gb = marginal6(value6);
elems(6) = P6gb;

%P9gb
marg9 = marginal_nodes( engine2, 9 );
marginal9 = marg9.T;
P9gb = marginal9(value9);
elems(7) = P9gb;

P69gb = P6gb*P9gb;

elems
z(bucket) = P69gb * Pbgactive;


z
prob_bucket = z ./ sum(z)
%prob_bucket = prob_bucket ./ prior10';
%pbs = sum(prob_bucket);
%prob_bucket = prob_bucket / pbs
n_samples = 100;
predicted_buckets = discretesample( prob_bucket, n_samples );
diff_sum = 0;
for i=1:n_samples
    diff_sum = diff_sum + abs(true_label - predicted_buckets(i));
end
avg_diff = diff_sum / n_samples

evidence = cell(1,N);
evidence{6} = value6;
evidence{9} = value9;
evidence{12} = value12;
evidence{13} = value13;
evidence{14} = value14;
evidence{15} = value15;
[engine2, ll] = enter_evidence(engine, evidence);
marg = marginal_nodes(engine2, 10);
marginal = marg.T
n_samples = 100;
predicted_buckets = discretesample( marginal, n_samples );
diff_sum = 0;
for i=1:n_samples
    diff_sum = diff_sum + abs(true_label - predicted_buckets(i));
end
avg_diff = diff_sum / n_samples



