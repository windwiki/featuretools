import copy

import pandas as pd
import pytest

import featuretools as ft
from featuretools.feature_base import (
    AggregationFeature,
    DirectFeature,
    IdentityFeature,
    TransformFeature
)
from featuretools.primitives import (  # CumMean,
    Absolute,
    AddNumeric,
    Count,
    CumCount,
    CumMean,
    CumSum,
    Day,
    Diff,
    Equal,
    Hour,
    IsIn,
    Last,
    Mean,
    Mode,
    Month,
    NMostCommon,
    NotEqual,
    NumCharacters,
    NumUnique,
    Sum,
    TimeSincePrevious,
    TransformPrimitive,
    Year
)
from featuretools.synthesis import DeepFeatureSynthesis
from featuretools.tests.testing_utils import feature_with_name
from featuretools.variable_types import Datetime, Numeric


def test_makes_agg_features_from_str(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='sessions',
                                   entityset=es,
                                   agg_primitives=['last'],
                                   trans_primitives=[])

    features = dfs_obj.build_features()
    assert (feature_with_name(features, 'LAST(log.value)'))


def test_makes_agg_features_from_mixed_str(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='sessions',
                                   entityset=es,
                                   agg_primitives=[Count, 'last'],
                                   trans_primitives=[])

    features = dfs_obj.build_features()
    assert (feature_with_name(features, 'LAST(log.value)'))
    assert (feature_with_name(features, 'COUNT(log)'))


def test_case_insensitive(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='sessions',
                                   entityset=es,
                                   agg_primitives=['MiN'],
                                   trans_primitives=['AbsOlute'])

    features = dfs_obj.build_features()
    assert (feature_with_name(features, 'MIN(log.value)'))
    assert (feature_with_name(features, 'ABSOLUTE(MIN(log.value_many_nans))'))


def test_makes_agg_features(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='sessions',
                                   entityset=es,
                                   agg_primitives=[Last],
                                   trans_primitives=[])

    features = dfs_obj.build_features()
    assert (feature_with_name(features, 'LAST(log.value)'))


def test_only_makes_supplied_agg_feat(es):
    kwargs = dict(
        target_entity_id='customers',
        entityset=es,
        max_depth=3,
    )
    dfs_obj = DeepFeatureSynthesis(agg_primitives=[Last], **kwargs)

    features = dfs_obj.build_features()

    def find_other_agg_features(features):
        return [f for f in features
                if (isinstance(f, AggregationFeature) and
                    not isinstance(f.primitive, Last)) or
                len([g for g in f.base_features
                     if isinstance(g, AggregationFeature) and
                     not isinstance(g.primitive, Last)]) > 0]

    other_agg_features = find_other_agg_features(features)
    assert len(other_agg_features) == 0


def test_error_for_missing_target_entity(es):
    error_text = 'Provided target entity missing_entity does not exist in ecommerce'
    with pytest.raises(KeyError, match=error_text):
        DeepFeatureSynthesis(target_entity_id='missing_entity',
                             entityset=es,
                             agg_primitives=[Last],
                             trans_primitives=[],
                             ignore_entities=['log'])

    es_without_id = ft.EntitySet()
    error_text = 'Provided target entity missing_entity does not exist in entity set'
    with pytest.raises(KeyError, match=error_text):
        DeepFeatureSynthesis(target_entity_id='missing_entity',
                             entityset=es_without_id,
                             agg_primitives=[Last],
                             trans_primitives=[],
                             ignore_entities=['log'])


def test_ignores_entities(es):
    error_text = 'ignore_entities must be a list'
    with pytest.raises(TypeError, match=error_text):
        DeepFeatureSynthesis(target_entity_id='sessions',
                             entityset=es,
                             agg_primitives=[Last],
                             trans_primitives=[],
                             ignore_entities='log')

    dfs_obj = DeepFeatureSynthesis(target_entity_id='sessions',
                                   entityset=es,
                                   agg_primitives=[Last],
                                   trans_primitives=[],
                                   ignore_entities=['log'])

    features = dfs_obj.build_features()
    for f in features:
        deps = f.get_dependencies(deep=True)
        entities = [d.entity.id for d in deps]
        assert 'log' not in entities


def test_ignores_variables(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='sessions',
                                   entityset=es,
                                   agg_primitives=[Last],
                                   trans_primitives=[],
                                   ignore_variables={'log': ['value']})
    features = dfs_obj.build_features()
    for f in features:
        deps = f.get_dependencies(deep=True)
        identities = [d for d in deps
                      if isinstance(d, IdentityFeature)]
        variables = [d.variable.id for d in identities
                     if d.entity.id == 'log']
        assert 'value' not in variables


def test_makes_dfeatures(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='sessions',
                                   entityset=es,
                                   agg_primitives=[],
                                   trans_primitives=[])

    features = dfs_obj.build_features()
    assert (feature_with_name(features, 'customers.age'))


def test_makes_trans_feat(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='log',
                                   entityset=es,
                                   agg_primitives=[],
                                   trans_primitives=[Hour])

    features = dfs_obj.build_features()
    assert (feature_with_name(features, 'HOUR(datetime)'))


def test_handles_diff_entity_groupby(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='log',
                                   entityset=es,
                                   agg_primitives=[],
                                   groupby_trans_primitives=[Diff])

    features = dfs_obj.build_features()
    assert (feature_with_name(features, 'DIFF(value) by session_id'))
    assert (feature_with_name(features, 'DIFF(value) by product_id'))


def test_handles_time_since_previous_entity_groupby(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='log',
                                   entityset=es,
                                   agg_primitives=[],
                                   groupby_trans_primitives=[TimeSincePrevious])

    features = dfs_obj.build_features()
    assert (feature_with_name(features, 'TIME_SINCE_PREVIOUS(datetime) by session_id'))

# M TODO
# def test_handles_cumsum_entity_groupby(es):
#     dfs_obj = DeepFeatureSynthesis(target_entity_id='sessions',
#                                    entityset=es,
#                                    agg_primitives=[],
#                                    trans_primitives=[CumMean])

#     features = dfs_obj.build_features()
#     assert (feature_with_name(features, u'customers.CUM_MEAN(age by région_id)'))


def test_only_makes_supplied_trans_feat(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='log',
                                   entityset=es,
                                   agg_primitives=[],
                                   trans_primitives=[Hour])

    features = dfs_obj.build_features()
    other_trans_features = [f for f in features
                            if (isinstance(f, TransformFeature) and
                                not isinstance(f.primitive, Hour)) or
                            len([g for g in f.base_features
                                 if isinstance(g, TransformFeature) and
                                 not isinstance(g.primitive, Hour)]) > 0]
    assert len(other_trans_features) == 0


def test_makes_dfeatures_of_agg_primitives(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='sessions',
                                   entityset=es,
                                   agg_primitives=[Last],
                                   trans_primitives=[])
    features = dfs_obj.build_features()
    assert (feature_with_name(features,
                              'customers.LAST(sessions.device_type)'))


def test_makes_agg_features_of_trans_primitives(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='sessions',
                                   entityset=es,
                                   agg_primitives=[Last],
                                   trans_primitives=[Hour])

    features = dfs_obj.build_features()
    assert (feature_with_name(features, 'LAST(log.HOUR(datetime))'))


def test_makes_agg_features_with_where(es):
    es.add_interesting_values()

    dfs_obj = DeepFeatureSynthesis(target_entity_id='sessions',
                                   entityset=es,
                                   agg_primitives=[Count],
                                   where_primitives=[Count],
                                   trans_primitives=[])

    features = dfs_obj.build_features()
    assert (feature_with_name(features,
                              'COUNT(log WHERE priority_level = 0)'))

    # make sure they are made using direct features too
    assert (feature_with_name(features,
                              'COUNT(log WHERE products.department = food)'))


def test_make_groupby_features(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='log',
                                   entityset=es,
                                   agg_primitives=[],
                                   trans_primitives=[],
                                   groupby_trans_primitives=['cum_sum'])
    features = dfs_obj.build_features()
    assert (feature_with_name(features,
                              "CUM_SUM(value) by session_id"))


def test_make_indirect_groupby_features(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='log',
                                   entityset=es,
                                   agg_primitives=[],
                                   trans_primitives=[],
                                   groupby_trans_primitives=['cum_sum'])
    features = dfs_obj.build_features()
    assert (feature_with_name(features,
                              "CUM_SUM(products.rating) by session_id"))


def test_make_groupby_features_with_id(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='sessions',
                                   entityset=es,
                                   agg_primitives=[],
                                   trans_primitives=[],
                                   groupby_trans_primitives=['cum_count'])
    features = dfs_obj.build_features()
    assert (feature_with_name(features, "CUM_COUNT(customer_id) by customer_id"))


def test_make_groupby_features_with_diff_id(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='customers',
                                   entityset=es,
                                   agg_primitives=[],
                                   trans_primitives=[],
                                   groupby_trans_primitives=['cum_count'])
    features = dfs_obj.build_features()
    groupby_with_diff_id = u"CUM_COUNT(cohort) by région_id"
    assert (feature_with_name(features, groupby_with_diff_id))


def test_make_groupby_features_with_agg(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='cohorts',
                                   entityset=es,
                                   agg_primitives=['sum'],
                                   trans_primitives=[],
                                   groupby_trans_primitives=['cum_sum'])
    features = dfs_obj.build_features()
    agg_on_groupby_name = u"SUM(customers.CUM_SUM(age) by région_id)"
    assert (feature_with_name(features, agg_on_groupby_name))


def test_bad_groupby_feature(es):
    msg = "Unknown transform primitive max"
    with pytest.raises(ValueError, match=msg):
        DeepFeatureSynthesis(target_entity_id='customers',
                             entityset=es,
                             agg_primitives=['sum'],
                             trans_primitives=[],
                             groupby_trans_primitives=['max'])


def test_abides_by_max_depth_param(es):
    for i in [1, 2, 3]:
        dfs_obj = DeepFeatureSynthesis(target_entity_id='sessions',
                                       entityset=es,
                                       agg_primitives=[Last],
                                       trans_primitives=[],
                                       max_depth=i)

        features = dfs_obj.build_features()
        for f in features:
            # last feature is identity feature which doesn't count
            assert (f.get_depth() <= i + 1)


def test_drop_contains(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='sessions',
                                   entityset=es,
                                   agg_primitives=[Last],
                                   trans_primitives=[],
                                   max_depth=1,
                                   seed_features=[],
                                   drop_contains=[])
    features = dfs_obj.build_features()
    to_drop = features[0]
    partial_name = to_drop.get_name()[:5]
    dfs_drop = DeepFeatureSynthesis(target_entity_id='sessions',
                                    entityset=es,
                                    agg_primitives=[Last],
                                    trans_primitives=[],
                                    max_depth=1,
                                    seed_features=[],
                                    drop_contains=[partial_name])
    features = dfs_drop.build_features()
    assert to_drop.get_name() not in [f.get_name() for f in features]


def test_drop_exact(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='sessions',
                                   entityset=es,
                                   agg_primitives=[Last],
                                   trans_primitives=[],
                                   max_depth=1,
                                   seed_features=[],
                                   drop_exact=[])
    features = dfs_obj.build_features()
    to_drop = features[0]
    name = to_drop.get_name()
    dfs_drop = DeepFeatureSynthesis(target_entity_id='sessions',
                                    entityset=es,
                                    agg_primitives=[Last],
                                    trans_primitives=[],
                                    max_depth=1,
                                    seed_features=[],
                                    drop_exact=[name])
    features = dfs_drop.build_features()
    assert name not in [f.get_name() for f in features]


def test_seed_features(es):
    seed_feature_sessions = ft.Feature(es['log']["id"], parent_entity=es['sessions'], primitive=Count) > 2
    seed_feature_log = ft.Feature(es['log']['datetime'], primitive=Hour)
    session_agg = ft.Feature(seed_feature_log, parent_entity=es['sessions'], primitive=Last)
    dfs_obj = DeepFeatureSynthesis(target_entity_id='sessions',
                                   entityset=es,
                                   agg_primitives=[Last],
                                   trans_primitives=[],
                                   max_depth=2,
                                   seed_features=[seed_feature_sessions,
                                                  seed_feature_log])
    features = dfs_obj.build_features()
    assert seed_feature_sessions.get_name() in [f.get_name()
                                                for f in features]
    assert session_agg.get_name() in [f.get_name() for f in features]


def test_does_not_make_agg_of_direct_of_target_entity(es):
    count_sessions = ft.Feature(es['sessions']["id"], parent_entity=es['customers'], primitive=Count)
    dfs_obj = DeepFeatureSynthesis(target_entity_id='customers',
                                   entityset=es,
                                   agg_primitives=[Last],
                                   trans_primitives=[],
                                   max_depth=2,
                                   seed_features=[count_sessions])
    features = dfs_obj.build_features()
    # this feature is meaningless because customers.COUNT(sessions) is already defined on
    # the customers entity
    assert not feature_with_name(features, 'LAST(sessions.customers.COUNT(sessions))')
    assert not feature_with_name(features, 'LAST(sessions.customers.age)')


def test_dfs_builds_on_seed_features_more_than_max_depth(es):
    seed_feature_sessions = ft.Feature(es['log']["id"], parent_entity=es['sessions'], primitive=Count)
    seed_feature_log = ft.Feature(es['log']['datetime'], primitive=Hour)
    session_agg = ft.Feature(seed_feature_log, parent_entity=es['sessions'], primitive=Last)

    # Depth of this feat is 2 relative to session_agg, the seed feature,
    # which is greater than max_depth so it shouldn't be built
    session_agg_trans = DirectFeature(ft.Feature(session_agg, parent_entity=es['customers'], primitive=Mode),
                                      es['sessions'])
    dfs_obj = DeepFeatureSynthesis(target_entity_id='sessions',
                                   entityset=es,
                                   agg_primitives=[Last, Count],
                                   trans_primitives=[],
                                   max_depth=1,
                                   seed_features=[seed_feature_sessions,
                                                  seed_feature_log])
    features = dfs_obj.build_features()
    assert seed_feature_sessions.get_name() in [f.get_name()
                                                for f in features]
    assert session_agg.get_name() in [f.get_name() for f in features]
    assert session_agg_trans.get_name() not in [f.get_name()
                                                for f in features]


def test_allowed_paths(es):
    kwargs = dict(
        target_entity_id='customers',
        entityset=es,
        agg_primitives=[Last],
        trans_primitives=[],
        max_depth=2,
        seed_features=[]
    )
    dfs_unconstrained = DeepFeatureSynthesis(**kwargs)
    features_unconstrained = dfs_unconstrained.build_features()

    unconstrained_names = [f.get_name() for f in features_unconstrained]
    customers_session_feat = ft.Feature(es['sessions']['device_type'], parent_entity=es['customers'], primitive=Last)
    customers_session_log_feat = ft.Feature(es['log']['value'], parent_entity=es['customers'], primitive=Last)
    assert customers_session_feat.get_name() in unconstrained_names
    assert customers_session_log_feat.get_name() in unconstrained_names

    dfs_constrained = DeepFeatureSynthesis(allowed_paths=[['customers',
                                                           'sessions']],
                                           **kwargs)
    features = dfs_constrained.build_features()
    names = [f.get_name() for f in features]
    assert customers_session_feat.get_name() in names
    assert customers_session_log_feat.get_name() not in names


def test_max_features(es):
    kwargs = dict(
        target_entity_id='customers',
        entityset=es,
        agg_primitives=[Last],
        trans_primitives=[],
        max_depth=2,
        seed_features=[]
    )
    dfs_unconstrained = DeepFeatureSynthesis(**kwargs)
    features_unconstrained = dfs_unconstrained.build_features()
    dfs_unconstrained_with_arg = DeepFeatureSynthesis(max_features=-1,
                                                      **kwargs)
    feats_unconstrained_with_arg = dfs_unconstrained_with_arg.build_features()
    dfs_constrained = DeepFeatureSynthesis(max_features=1, **kwargs)
    features = dfs_constrained.build_features()
    assert len(features_unconstrained) == len(feats_unconstrained_with_arg)
    assert len(features) == 1


def test_where_primitives(es):
    es = copy.deepcopy(es)
    es['sessions']['device_type'].interesting_values = [0]
    kwargs = dict(
        target_entity_id='customers',
        entityset=es,
        agg_primitives=[Count, Last],
        trans_primitives=[Absolute],
        max_depth=3,
    )
    dfs_unconstrained = DeepFeatureSynthesis(**kwargs)
    dfs_constrained = DeepFeatureSynthesis(where_primitives=['last'], **kwargs)
    features_unconstrained = dfs_unconstrained.build_features()
    features = dfs_constrained.build_features()

    where_feats_unconstrained = [f for f in features_unconstrained
                                 if isinstance(f, AggregationFeature) and f.where is not None]
    where_feats = [f for f in features
                   if isinstance(f, AggregationFeature) and f.where is not None]

    assert len(where_feats_unconstrained) >= 1

    assert len([f for f in where_feats_unconstrained
                if isinstance(f.primitive, Last)]) == 0
    assert len([f for f in where_feats_unconstrained
                if isinstance(f.primitive, Count)]) > 0

    assert len([f for f in where_feats
                if isinstance(f.primitive, Last)]) > 0
    assert len([f for f in where_feats
                if isinstance(f.primitive, Count)]) == 0
    assert len([d for f in where_feats
                for d in f.get_dependencies(deep=True)
                if isinstance(d.primitive, Absolute)]) > 0


def test_stacking_where_primitives(es):
    es = copy.deepcopy(es)
    es['sessions']['device_type'].interesting_values = [0]
    es['log']['product_id'].interesting_values = ["coke_zero"]
    kwargs = dict(
        target_entity_id='customers',
        entityset=es,
        agg_primitives=[Count, Last],
        max_depth=3,
    )
    dfs_where_stack_limit_1 = DeepFeatureSynthesis(where_primitives=['last', Count],
                                                   **kwargs)
    dfs_where_stack_limit_2 = DeepFeatureSynthesis(where_primitives=['last', Count],
                                                   where_stacking_limit=2,
                                                   **kwargs)
    stack_limit_1_features = dfs_where_stack_limit_1.build_features()
    stack_limit_2_features = dfs_where_stack_limit_2.build_features()

    where_stack_1_feats = [f for f in stack_limit_1_features
                           if isinstance(f, AggregationFeature) and f.where is not None]
    where_stack_2_feats = [f for f in stack_limit_2_features
                           if isinstance(f, AggregationFeature) and f.where is not None]

    assert len(where_stack_1_feats) >= 1
    assert len(where_stack_2_feats) >= 1

    assert len([f for f in where_stack_1_feats
                if isinstance(f.primitive, Last)]) > 0
    assert len([f for f in where_stack_1_feats
                if isinstance(f.primitive, Count)]) > 0

    assert len([f for f in where_stack_2_feats
                if isinstance(f.primitive, Last)]) > 0
    assert len([f for f in where_stack_2_feats
                if isinstance(f.primitive, Count)]) > 0

    stacked_where_limit_1_feats = []
    stacked_where_limit_2_feats = []
    where_double_where_tuples = [
        (where_stack_1_feats, stacked_where_limit_1_feats),
        (where_stack_2_feats, stacked_where_limit_2_feats)
    ]
    for where_list, double_where_list in where_double_where_tuples:
        for feature in where_list:
            for base_feat in feature.base_features:
                if isinstance(base_feat, AggregationFeature) and base_feat.where is not None:
                    double_where_list.append(feature)

    assert len(stacked_where_limit_1_feats) == 0
    assert len(stacked_where_limit_2_feats) > 0


def test_where_different_base_feats(es):
    es = copy.deepcopy(es)
    es['sessions']['device_type'].interesting_values = [0]

    kwargs = dict(
        target_entity_id='customers',
        entityset=es,
        agg_primitives=[Last, Count],
        where_primitives=[Last, Count],
        max_depth=3,
    )
    dfs_unconstrained = DeepFeatureSynthesis(**kwargs)
    features = dfs_unconstrained.build_features()
    where_feats = [f.unique_name() for f in features
                   if isinstance(f, AggregationFeature) and f.where is not None]
    not_where_feats = [f.unique_name() for f in features
                       if isinstance(f, AggregationFeature) and f.where is None]
    for name in not_where_feats:
        assert name not in where_feats


def test_dfeats_where(es):
    es.add_interesting_values()

    dfs_obj = DeepFeatureSynthesis(target_entity_id='sessions',
                                   entityset=es,
                                   agg_primitives=[Count],
                                   trans_primitives=[])

    features = dfs_obj.build_features()

    # test to make sure we build direct features of agg features with where clause
    assert (feature_with_name(
        features, 'customers.COUNT(log WHERE priority_level = 0)'))

    assert (feature_with_name(
        features, 'COUNT(log WHERE products.department = electronics)'))


def test_commutative(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='log',
                                   entityset=es,
                                   agg_primitives=[Sum],
                                   trans_primitives=[AddNumeric],
                                   max_depth=3)
    feats = dfs_obj.build_features()

    add_feats = [f for f in feats if isinstance(f.primitive, AddNumeric)]

    # Check that there are no two AddNumeric features with the same base
    # features.
    unordered_args = set()
    for f in add_feats:
        arg1, arg2 = f.base_features
        args_set = frozenset({arg1.unique_name(), arg2.unique_name()})
        unordered_args.add(args_set)

    assert len(add_feats) == len(unordered_args)


def test_transform_consistency():
    # Create dataframe
    df = pd.DataFrame({'a': [14, 12, 10], 'b': [False, False, True],
                       'b1': [True, True, False], 'b12': [4, 5, 6],
                       'P': [10, 15, 12]})
    es = ft.EntitySet(id='test')
    # Add dataframe to entityset
    es.entity_from_dataframe(entity_id='first', dataframe=df,
                             index='index',
                             make_index=True)

    # Generate features
    feature_defs = ft.dfs(entityset=es, target_entity='first',
                          trans_primitives=['and', 'add_numeric', 'or'],
                          features_only=True)

    # Check for correct ordering of features
    assert feature_with_name(feature_defs, 'a')
    assert feature_with_name(feature_defs, 'b')
    assert feature_with_name(feature_defs, 'b1')
    assert feature_with_name(feature_defs, 'b12')
    assert feature_with_name(feature_defs, 'P')
    assert feature_with_name(feature_defs, 'AND(b, b1)')
    assert not feature_with_name(feature_defs, 'AND(b1, b)')  # make sure it doesn't exist the other way
    assert feature_with_name(feature_defs, 'a + P')
    assert feature_with_name(feature_defs, 'b12 + P')
    assert feature_with_name(feature_defs, 'a + b12')
    assert feature_with_name(feature_defs, 'OR(b, b1)')
    assert feature_with_name(feature_defs, 'OR(AND(b, b1), b)')
    assert feature_with_name(feature_defs, 'OR(AND(b, b1), b1)')


def test_transform_no_stack_agg(es):
    feature_defs = ft.dfs(entityset=es,
                          target_entity="customers",
                          agg_primitives=[NMostCommon],
                          trans_primitives=[NotEqual],
                          max_depth=3,
                          features_only=True)
    assert not feature_with_name(feature_defs, 'id != N_MOST_COMMON(sessions.device_type)')


def test_intialized_trans_prim(es):
    prim = IsIn(list_of_outputs=['coke zero'])
    dfs_obj = DeepFeatureSynthesis(target_entity_id='log',
                                   entityset=es,
                                   agg_primitives=[],
                                   trans_primitives=[prim])

    features = dfs_obj.build_features()
    assert (feature_with_name(features, "product_id.isin(['coke zero'])"))


def test_initialized_agg_prim(es):
    ThreeMost = NMostCommon(n=3)
    dfs_obj = DeepFeatureSynthesis(target_entity_id="sessions",
                                   entityset=es,
                                   agg_primitives=[ThreeMost],
                                   trans_primitives=[])
    features = dfs_obj.build_features()
    assert (feature_with_name(features, "N_MOST_COMMON(log.product_id)"))


def test_return_variable_types(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id="sessions",
                                   entityset=es,
                                   agg_primitives=[Count, NMostCommon],
                                   trans_primitives=[Absolute, Hour, IsIn])

    discrete = ft.variable_types.Discrete
    numeric = ft.variable_types.Numeric
    datetime = ft.variable_types.Datetime

    f1 = dfs_obj.build_features(return_variable_types=None)
    f2 = dfs_obj.build_features(return_variable_types=[discrete])
    f3 = dfs_obj.build_features(return_variable_types="all")
    f4 = dfs_obj.build_features(return_variable_types=[datetime])

    f1_types = set([f.variable_type for f in f1])
    f2_types = set([f.variable_type for f in f2])
    f3_types = set([f.variable_type for f in f3])
    f4_types = set([f.variable_type for f in f4])

    assert(discrete in f1_types)
    assert(numeric in f1_types)
    assert(datetime not in f2_types)

    assert(discrete in f2_types)
    assert(numeric not in f2_types)
    assert(datetime not in f2_types)

    assert(discrete in f3_types)
    assert(numeric in f3_types)
    assert(datetime in f3_types)

    assert(discrete not in f4_types)
    assert(numeric not in f4_types)
    assert(datetime in f4_types)


def test_checks_primitives_correct_type(es):
    error_text = "Primitive <class \\'featuretools\\.primitives\\.standard\\."\
                 "transform_primitive\\.Hour\\'> in agg_primitives is not an "\
                 "aggregation primitive"
    with pytest.raises(ValueError, match=error_text):
        DeepFeatureSynthesis(target_entity_id="sessions",
                             entityset=es,
                             agg_primitives=[Hour],
                             trans_primitives=[])

    error_text = "Primitive <class \\'featuretools\\.primitives\\.standard\\."\
                 "aggregation_primitives\\.Last\\'> in trans_primitives or "\
                 "groupby_trans_primitives is not a transform primitive"
    with pytest.raises(ValueError, match=error_text):
        DeepFeatureSynthesis(target_entity_id="sessions",
                             entityset=es,
                             agg_primitives=[],
                             trans_primitives=[Last])


def test_makes_agg_features_along_multiple_paths(diamond_es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='regions',
                                   entityset=diamond_es,
                                   agg_primitives=['mean'],
                                   trans_primitives=[])

    features = dfs_obj.build_features()
    assert feature_with_name(features, 'MEAN(customers.transactions.amount)')
    assert feature_with_name(features, 'MEAN(stores.transactions.amount)')


def test_makes_direct_features_through_multiple_relationships(games_es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='games',
                                   entityset=games_es,
                                   agg_primitives=['mean'],
                                   trans_primitives=[])

    features = dfs_obj.build_features()

    teams = ['home', 'away']
    for forward in teams:
        for backward in teams:
            for var in teams:
                f = 'teams[%s_team_id].MEAN(games[%s_team_id].%s_team_score)' \
                    % (forward, backward, var)
                assert feature_with_name(features, f)


def test_stacks_multioutput_features(es):
    class TestTime(TransformPrimitive):
        name = "test_time"
        input_types = [Datetime]
        return_type = Numeric
        number_output_features = 6

        def get_function(self):
            def test_f(x):
                times = pd.Series(x)
                units = ["year", "month", "day", "hour", "minute", "second"]
                return [times.apply(lambda x: getattr(x, unit)) for unit in units]
            return test_f

    feat = ft.dfs(entityset=es,
                  target_entity="customers",
                  agg_primitives=[NumUnique, NMostCommon(n=3)],
                  trans_primitives=[TestTime, Diff],
                  max_depth=4,
                  features_only=True
                  )

    for i in range(3):
        f = 'NUM_UNIQUE(sessions.N_MOST_COMMON(log.countrycode)[%d])' % i
        assert feature_with_name(feat, f)

    for i in range(6):
        f = 'DIFF(TEST_TIME(date_of_birth)[%d])' % i
        assert feature_with_name(feat, f)


def test_seed_multi_output_feature_stacking(es):
    threecommon = NMostCommon(3)
    tc = ft.Feature(es['log']['product_id'], parent_entity=es["sessions"], primitive=threecommon)

    fm, feat = ft.dfs(entityset=es,
                      target_entity="customers",
                      seed_features=[tc],
                      agg_primitives=[NumUnique],
                      trans_primitives=[],
                      max_depth=4
                      )

    for i in range(3):
        f = 'NUM_UNIQUE(sessions.N_MOST_COMMON(log.product_id)[%d])' % i
        assert feature_with_name(feat, f)


def test_makes_direct_features_along_multiple_paths(diamond_es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='transactions',
                                   entityset=diamond_es,
                                   max_depth=3,
                                   agg_primitives=[],
                                   trans_primitives=[])

    features = dfs_obj.build_features()
    assert feature_with_name(features, 'customers.regions.name')
    assert feature_with_name(features, 'stores.regions.name')


def test_does_not_make_trans_of_single_direct_feature(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='sessions',
                                   entityset=es,
                                   agg_primitives=[],
                                   trans_primitives=['weekday'],
                                   max_depth=2)

    features = dfs_obj.build_features()

    assert not feature_with_name(features, 'WEEKDAY(customers.signup_date)')
    assert feature_with_name(features, 'customers.WEEKDAY(signup_date)')


def test_makes_trans_of_multiple_direct_features(diamond_es):
    es = diamond_es
    dfs_obj = DeepFeatureSynthesis(target_entity_id='transactions',
                                   entityset=es,
                                   agg_primitives=['mean'],
                                   trans_primitives=[Equal],
                                   max_depth=4)

    features = dfs_obj.build_features()

    # Make trans of direct and non-direct
    assert feature_with_name(features, 'amount = stores.MEAN(transactions.amount)')

    # Make trans of direct features on different entities
    assert feature_with_name(features, 'customers.MEAN(transactions.amount) = stores.square_ft')

    # Make trans of direct features on same entity with different paths.
    assert feature_with_name(features, 'customers.regions.name = stores.regions.name')

    # Don't make trans of direct features with same path.
    assert not feature_with_name(features, 'stores.square_ft = stores.MEAN(transactions.amount)')
    assert not feature_with_name(features, 'stores.MEAN(transactions.amount) = stores.square_ft')

    # The naming of the below is confusing but this is a direct feature of a transform.
    assert feature_with_name(features, 'stores.MEAN(transactions.amount) = square_ft')


def test_makes_direct_of_agg_of_trans_on_target(es):
    dfs_obj = DeepFeatureSynthesis(target_entity_id='log',
                                   entityset=es,
                                   agg_primitives=['mean'],
                                   trans_primitives=[Absolute],
                                   max_depth=3)

    features = dfs_obj.build_features()
    assert feature_with_name(features, 'sessions.MEAN(log.ABSOLUTE(value))')


def test_primitive_options_errors(es):
    wrong_key_options = {'mode': {'ignore_entity': ['sessions']}}
    wrong_type_list = {'mode': {'ignore_entities': 'sessions'}}
    wrong_type_dict = {'mode':
                       {'ignore_variables': {'sessions': 'product_id'}}}
    conflicting_primitive_options = {('count', 'mode'):
                                     {'ignore_entities': ['sessions']},
                                     'mode': {'include_entities': ['sessions']}}
    invalid_entity = {'mode': {'include_entities': ['invalid_entity']}}
    invalid_variable_entity = {'mode': {'include_variables': {'invalid_entity': ['product_id']}}}
    invalid_variable = {'mode': {'include_variables': {'sessions': ['invalid_variable']}}}
    key_error_text = "Unrecognized primitive option \'ignore_entity\' for mode"
    list_error_text = "Incorrect type formatting for \'ignore_entities\' for mode"
    dict_error_text = "Incorrect type formatting for \'ignore_variables\' for mode"
    conflicting_error_text = "Multiple options found for primitive mode"
    invalid_entity_warning = "Entity \'invalid_entity\' not in entityset"
    invalid_variable_warning = "Variable \'invalid_variable\' not in entity \'sessions\'"
    with pytest.raises(KeyError, match=key_error_text):
        DeepFeatureSynthesis(target_entity_id='customers',
                             entityset=es,
                             agg_primitives=['mode'],
                             trans_primitives=[],
                             primitive_options=wrong_key_options)
    with pytest.raises(TypeError, match=list_error_text):
        DeepFeatureSynthesis(target_entity_id='customers',
                             entityset=es,
                             agg_primitives=['mode'],
                             trans_primitives=[],
                             primitive_options=wrong_type_list)
    with pytest.raises(TypeError, match=dict_error_text):
        DeepFeatureSynthesis(target_entity_id='customers',
                             entityset=es,
                             agg_primitives=['mode'],
                             trans_primitives=[],
                             primitive_options=wrong_type_dict)
    with pytest.raises(KeyError, match=conflicting_error_text):
        DeepFeatureSynthesis(target_entity_id='customers',
                             entityset=es,
                             agg_primitives=['mode'],
                             trans_primitives=[],
                             primitive_options=conflicting_primitive_options)
    with pytest.warns(UserWarning, match=invalid_entity_warning) as record:
        DeepFeatureSynthesis(target_entity_id='customers',
                             entityset=es,
                             agg_primitives=['mode'],
                             trans_primitives=[],
                             primitive_options=invalid_entity)
    assert len(record) == 1
    with pytest.warns(UserWarning, match=invalid_entity_warning) as record:
        DeepFeatureSynthesis(target_entity_id='customers',
                             entityset=es,
                             agg_primitives=['mode'],
                             trans_primitives=[],
                             primitive_options=invalid_variable_entity)
    assert len(record) == 1
    with pytest.warns(UserWarning, match=invalid_variable_warning) as record:
        DeepFeatureSynthesis(target_entity_id='customers',
                             entityset=es,
                             agg_primitives=['mode'],
                             trans_primitives=[],
                             primitive_options=invalid_variable)
    assert len(record) == 1


def test_primitive_options(es):
    options = {'sum': {'include_variables': {'customers': ['age']}},
               'mean': {'include_entities': ['customers']},
               'mode': {'ignore_entities': ['sessions']},
               'num_unique': {'ignore_variables': {'customers': ['engagement_level']}}}
    dfs_obj = DeepFeatureSynthesis(target_entity_id='cohorts',
                                   entityset=es,
                                   primitive_options=options)
    features = dfs_obj.build_features()
    for f in features:
        deps = f.get_dependencies()
        entities = [d.entity.id for d in deps]
        identities = [d for d in deps if isinstance(d, IdentityFeature)]
        variables = [d.variable.id for d in identities]
        if isinstance(f.primitive, Sum):
            if 'customers' in entities:
                assert 'age' in variables or variables == []
        if isinstance(f.primitive, Mean):
            assert 'customers' in entities
        if isinstance(f.primitive, Mode):
            assert 'sessions' not in entities
        if isinstance(f.primitive, NumUnique):
            if 'customers' in entities:
                assert 'engagement_level' not in variables

    options = {'month': {'ignore_variables': {'customers': ['date_of_birth']}},
               'day': {'include_variables': {'customers': ['signup_date', 'upgrade_date']}},
               'num_characters': {'ignore_entities': ['customers']},
               'year': {'include_entities': ['customers']}}
    dfs_obj = DeepFeatureSynthesis(target_entity_id='customers',
                                   entityset=es,
                                   agg_primitives=[],
                                   ignore_entities=['cohort'],
                                   primitive_options=options)
    features = dfs_obj.build_features()
    assert not any([isinstance(f, NumCharacters) for f in features])
    for f in features:
        deps = f.get_dependencies()
        entities = [d.entity.id for d in deps]
        identities = [d for d in deps if isinstance(d, IdentityFeature)]
        variables = [d.variable.id for d in identities]
        if isinstance(f.primitive, Month):
            if 'customers' in entities:
                assert 'date_of_birth' not in variables
        if isinstance(f.primitive, Day):
            if 'customers' in entities:
                assert 'signup_date' in variables or 'upgrade_date' in variables
        if isinstance(f.primitive, Year):
            assert 'customers' in entities


def test_primitive_options_with_globals(es):
    # non-overlapping ignore_entities
    options = {'mode': {'ignore_entities': ['sessions']}}
    dfs_obj = DeepFeatureSynthesis(target_entity_id='cohorts',
                                   entityset=es,
                                   ignore_entities=[u'régions'],
                                   primitive_options=options)
    features = dfs_obj.build_features()
    for f in features:
        deps = f.get_dependencies(deep=True)
        entities = [d.entity.id for d in deps]
        assert u'régions' not in entities
        if isinstance(f.primitive, Mode):
            assert 'sessions' not in entities

    # non-overlapping ignore_variables
    options = {'num_unique': {'ignore_variables': {'customers': ['engagement_level']}}}
    dfs_obj = DeepFeatureSynthesis(target_entity_id='cohorts',
                                   entityset=es,
                                   ignore_variables={'customers': [u'région_id']},
                                   primitive_options=options)
    features = dfs_obj.build_features()
    for f in features:
        deps = f.get_dependencies()
        entities = [d.entity.id for d in deps]
        identities = [d for d in deps if isinstance(d, IdentityFeature)]
        variables = [d.variable.id for d in identities]
        if 'customers' in entities:
            assert u'region_id' not in variables
        if isinstance(f.primitive, NumUnique):
            if 'customers' in entities:
                assert 'engagement_level' not in variables

    # Overlapping globals/options with ignore_entities
    options = {'mode': {'include_entities': ['sessions', 'customers'],
                        'ignore_variables': {'customers': [u'région_id']}},
               'num_unique': {'include_entities': ['sessions', 'customers'],
                              'include_variables': {'sessions': ['device_type']}},
               'month': {'ignore_variables': {'cohorts': ['cohort_end']}}}
    dfs_obj = DeepFeatureSynthesis(target_entity_id='cohorts',
                                   entityset=es,
                                   ignore_entities=['sessions'],
                                   ignore_variables={'customers': ['age']},
                                   primitive_options=options)
    features = dfs_obj.build_features()
    for f in features:
        assert f.primitive.name != 'month'
        # ignoring cohorts means no features are created
        assert not isinstance(f.primitive, Month)

        deps = f.get_dependencies()
        entities = [d.entity.id for d in deps]
        identities = [d for d in deps if isinstance(d, IdentityFeature)]
        variables = [d.variable.id for d in identities]
        if isinstance(f.primitive, Mode):
            assert 'sessions' in entities or 'customers' in entities
            if 'customers' in entities:
                assert 'age' not in variables
                assert u'région_id' not in variables
        elif isinstance(f.primitive, NumUnique):
            assert 'sessions' in entities or 'customers' in entities
            if 'sessions' in entities:
                assert 'device_type' in variables or variables == []
        # All other primitives ignore 'sessions' and 'age'
        else:
            assert 'sessions' not in entities
            if 'customers' in entities:
                assert 'age' not in variables


def test_primitive_options_groupbys(es):
    options = {'cum_sum': {'include_groupby_variables': {'customers': [u'région_id']},
                           'ignore_groupby_variables': {'sessions': ['customer_id']}},
               'cum_mean': {'ignore_groupby_variables': {'customers': [u'région_id',
                                                                       'id']}},
               'cum_count': {'include_entities': ['customers'],
                             'include_groupby_variables': {'customers': [u"région_id",
                                                                         "cohort"]}},
               'cum_min': {'ignore_entities': ['customers']},
               'cum_max': {'include_entities': ['cohorts']}}
    dfs_obj = DeepFeatureSynthesis(target_entity_id='customers',
                                   entityset=es,
                                   groupby_trans_primitives=['cum_sum',
                                                             'cum_count',
                                                             'cum_min',
                                                             'cum_max',
                                                             'cum_mean'],
                                   primitive_options=options)
    features = dfs_obj.build_features()
    assert feature_with_name(features, u'CUM_SUM(age) by région_id')
    for f in features:
        # These either have nothing to groupby or don't include the target entity so shouldn't create features
        assert f.primitive.name not in ['cum_min', 'cum_max', 'cum_max']
        if isinstance(f.primitive, CumMean):
            assert f.groupby.variable.id not in [u'région_id', 'id']
        if isinstance(f.primitive, CumCount):
            assert f.groupby.variable.id in [u'région_id', 'cohort']
        if isinstance(f.primitive, CumSum):
            deps = f.get_dependencies()
            entities = [d.entity.id for d in deps]
            if 'customers' in entities:
                assert f.groupby.variable.id == u'région_id'


def test_primitive_options_multiple_inputs(es):
    too_many_options = {'mode': [{'include_entities': ['logs']},
                                 {'ignore_entities': ['sessions']}]}
    error_msg = "Number of options does not match number of inputs for primitive mode"
    with pytest.raises(AssertionError, match=error_msg):
        DeepFeatureSynthesis(target_entity_id='customers',
                             entityset=es,
                             agg_primitives=['mode'],
                             trans_primitives=[],
                             primitive_options=too_many_options)

    options = {'trend': [{'include_entities': ['log'],
                          'ignore_variables': {'log': ['value']}},
                         {'include_entities': ['log'],
                          'include_variables': {'log': ['datetime']}}]}
    dfs_obj = DeepFeatureSynthesis(target_entity_id='sessions',
                                   entityset=es,
                                   agg_primitives=['trend'],
                                   trans_primitives=[],
                                   primitive_options=options)
    features = dfs_obj.build_features()
    for f in features:
        deps = f.get_dependencies()
        entities = [d.entity.id for d in deps]
        identities = [d for d in deps if isinstance(d, IdentityFeature)]
        variables = [d.variable.id for d in identities]
        if f.primitive.name == 'trend':
            assert 'log' in entities
            assert 'datetime' in variables
            if len(variables) == 2:
                assert 'value' != variables[0]
