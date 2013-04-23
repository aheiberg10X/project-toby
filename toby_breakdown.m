
engine = jtree_inf_engine(bnet_learned);

true_label = 7; 

s=struct(bnet_learned.CPD{10});
prior10 = s.CPT;

z = zeros(1,10);

value12 = 1;
value13 = 5;
value14 = 6;
value15 = 3;

%value12 = 5;
%value13 = 3;
%value14 = 5;
%value15 = 8;

%value12 = 1;
%value13 = 3;
%value14 = 5;
%value15 = 8;

for bucket=1:10
    elems = zeros(1,5);
    bucket

    evidence1 = cell(1,N);
    evidence1{10} = bucket;
    evidence1{12} = value12;
    evidence1{13} = value13;
    evidence1{14} = value14;
    [engine2, ll] = enter_evidence(engine, evidence1);
    marg15 = marginal_nodes(engine2, 15);
    marginal15 = marg15.T;
    A = marginal15(value15);
    elems(1) = A;

    evidence2 = cell(1,N);
    evidence2{10} = bucket;
    evidence2{12} = value12;
    evidence2{13} = value13;
    [engine2, ll] = enter_evidence(engine, evidence2);
    marg14 = marginal_nodes(engine2, 14);
    marginal14 = marg14.T;
    B = marginal14(value14);
    elems(2) = B;

    evidence3 = cell(1,N);
    evidence3{10} = bucket;
    evidence3{12} = value12;
    [engine2, ll] = enter_evidence(engine, evidence3);
    marg13 = marginal_nodes(engine2, 13);
    marginal13 = marg13.T;
    C = marginal13(value13);
    elems(3) = C;

    evidence4 = cell(1,N);
    evidence4{10} = bucket;
    [engine2, ll] = enter_evidence(engine, evidence4);
    marg12 = marginal_nodes(engine2, 12);
    marginal12 = marg12.T;
    D = marginal12(value12);
    elems(4) = D;

    E = prior10(bucket);
    elems(5) = E;
    
    elems
    abc = A*B*C*D*E;
    %abc = B*C;
    z(bucket) = abc;
    
end

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
evidence{12} = value12;
evidence{13} = value13;
evidence{14} = value14;
evidence{15} = value15;
%this is still predicting very 1,2 heavy, even though every training example
%is not 0 or 1
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



