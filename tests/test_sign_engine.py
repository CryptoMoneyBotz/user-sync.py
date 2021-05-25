import logging
from unittest.mock import MagicMock

import pytest
from mock import MagicMock

from user_sync.config.sign_sync import SignConfigLoader
from user_sync.engine.sign import SignSyncEngine
from user_sync.engine.umapi import AdobeGroup


@pytest.fixture
def example_engine(default_sign_args):
    config = SignConfigLoader(default_sign_args)
    rule_config = config.get_engine_options()
    return SignSyncEngine(rule_config)


def test_load_users_and_groups(example_engine, example_user):
    dc = MagicMock()
    example_user['groups'] = ["Sign Users 1"]
    user = {'user@example.com': example_user}

    def dir_user_replacement(*args, **kwargs):
        return user.values()

    dc.load_users_and_groups = dir_user_replacement
    mapping = {}
    AdobeGroup.index_map = {}
    adobe_groups = [AdobeGroup('Group 1', 'primary')]
    mapping['Sign Users'] = {'groups': adobe_groups}
    example_engine.read_desired_user_groups(mapping, dc)
    assert example_engine.directory_user_by_user_key == user


def test_get_directory_user_key(example_engine, example_user):
    # user = {'user@example.com': example_user}
    # if the method is passed a dict with an email, it should return the email key
    assert example_engine.get_directory_user_key(
        example_user) == example_user['email']
    # if the user object passed in has no email value, it should return None
    assert example_engine.get_directory_user_key(
        {'': {'username': 'user@example.com'}}) is None


def test_handle_sign_only_users(example_engine, example_user):
    sign_connector = MagicMock()
    directory_users = {}
    adobeGroup = AdobeGroup('Group 1', 'primary')
    directory_users['federatedID, example.user@signtest.com'] = {
        'email': 'example.user@signtest.com',
        'sign_groups': {'groups': [adobeGroup]}
    }
    sign_users = {}
    sign_users['example.user@signtest.com'] = {
        'email': 'example.user@signtest.com', 'userId': 'somerandomhexstring'}

    def get_users():
        return sign_users

    def deactivate_user(insert_data):
        pass

    def check_sign_max_limit(org_name):
        pass

    sign_connector.deactivate_user = deactivate_user
    sign_connector.get_users = get_users
    example_engine.logger = logging.getLogger()
    example_engine.sign_users_by_org = {'primary': sign_users}
    example_engine.check_sign_max_limit = check_sign_max_limit
    org_name = 'primary'

    default_group_id = 'somerandomGROUPID'
    example_engine.handle_sign_only_users(sign_connector, org_name, default_group_id)
    assert True
    assert sign_users['example.user@signtest.com']['email'] == 'example.user@signtest.com'


def test_roles_match():
    resolved_role = ['GROUP_ADMIN', 'ACCOUNT_ADMIN']
    sign_role = ['ACCOUNT_ADMIN', 'GROUP_ADMIN']
    assert SignSyncEngine.roles_match(resolved_role, sign_role)
    assert not SignSyncEngine.roles_match(resolved_role, [])

    resolved_roles = ['ACCOUNT_ADMIN', 'GROUP_ADMIN', 'NORMAL_USER']
    sign_roles = ['ACCOUNT_ADMIN', 'GROUP_ADMIN', 'NORMAL_USER']
    assert SignSyncEngine.roles_match(resolved_roles, sign_roles) is True

    resolved_roles = ['GROUP_ADMIN', 'NORMAL_USER', 'ACCOUNT_ADMIN']
    sign_roles = ['ACCOUNT_ADMIN', 'GROUP_ADMIN', 'NORMAL_USER']
    assert SignSyncEngine.roles_match(resolved_roles, sign_roles) is True

    resolved_roles = []
    sign_roles = []
    assert SignSyncEngine.roles_match(resolved_roles, sign_roles) is True

    resolved_roles = ['normal_user']
    sign_roles = ['NORMAL_USER']
    assert SignSyncEngine.roles_match(resolved_roles, sign_roles) is False

    resolved_roles = ['NORMAL_USER', 'ACCOUNT_ADMIN']
    sign_roles = ['GROUP_ADMIN', 'NORMAL_USER']
    assert SignSyncEngine.roles_match(resolved_roles, sign_roles) is False


def test_should_sync():
    AdobeGroup.index_map = {}
    dir_user = {'sign_group': {'group': AdobeGroup.create('test group')}}
    assert SignSyncEngine.should_sync(dir_user, None)
    assert not SignSyncEngine.should_sync(dir_user, 'secondary')


def test_retrieve_admin_role():
    user = {'sign_group': {'roles': ['ACCOUNT_ADMIN', 'GROUP_ADMIN']}}
    assert SignSyncEngine.retrieve_admin_role(user) == sorted(['ACCOUNT_ADMIN', 'GROUP_ADMIN'])


def test_retrieve_assignment_group():
    AdobeGroup.index_map = {}
    user = {'sign_group': {'group': AdobeGroup.create('Test Group')}}
    assert SignSyncEngine.retrieve_assignment_group(user) == 'Test Group'
    user['sign_group']['group'] = None
    assert SignSyncEngine.retrieve_assignment_group(user) is None


def test__groupify():
    AdobeGroup.index_map = {}
    g1 = AdobeGroup.create('Sign Group 1')
    g2 = AdobeGroup.create('Sign Group 2')
    g3 = AdobeGroup.create('sec::Sign Group 3')

    processed_groups = SignSyncEngine._groupify(None, [{'groups': [g1, g2, g3]}])
    assert processed_groups == ['Sign Group 1', 'Sign Group 2']
    processed_groups = SignSyncEngine._groupify("sec", [{'groups': [g1, g2, g3]}])
    assert processed_groups == ['Sign Group 3']


def test_read_desired_user_groups(example_engine, example_user):
    dc = MagicMock()
    example_user['groups'] = ["Sign Users 1"]
    user = {'user@example.com': example_user}

    def dir_user_replacement(*args, **kwargs):
        return user.values()

    dc.load_users_and_groups = dir_user_replacement
    mapping = {}
    AdobeGroup.index_map = {}
    adobe_groups = [AdobeGroup('Group 1', 'primary')]
    mapping['Sign Users'] = {'groups': adobe_groups}
    example_engine.read_desired_user_groups(mapping, dc)
    assert example_engine.directory_user_by_user_key == user


def test_extract_mapped_group():
    AdobeGroup.index_map = {}

    def check_mapping(user_groups, group, roles):
        res = SignSyncEngine.extract_mapped_group(user_groups, mappings)
        if group is None:
            assert res['group'] is None
        else:
            assert AdobeGroup.create(group) == res['group']
        for r in roles:
            assert r in res['roles']

    g1 = AdobeGroup.create('Sign Group 1')
    g2 = AdobeGroup.create('Sign Group 2')
    g3 = AdobeGroup.create('Sign Group 3')

    mappings = {
        'Sign Group 1': {
            'priority': 0,
            'roles': set(),
            'groups': [g1]
        },
        'Test Group Admins 1': {
            'priority': 4,
            'roles': {'GROUP_ADMIN'},
            'groups': []
        },
        'Sign Group 2': {
            'priority': 2,
            'roles': set(),
            'groups': [g2, g1, g3]
        },
        'Test Group Admins 2': {
            'priority': 1,
            'roles': {'ACCOUNT_ADMIN'},
            'groups': []
        },
        'Sign Group 3': {
            'priority': 3,
            'roles': set(),
            'groups': [g3]
        },
        'Test Group Admins 3': {
            'priority': 5,
            'roles': {'ACCOUNT_ADMIN', 'GROUP_ADMIN'},
            'groups': [g2]
        },
    }

    check_mapping([], None, ['NORMAL_USER'])
    check_mapping(['Not A Group'], None, ['NORMAL_USER'])
    check_mapping(['Sign Group 1'], 'Sign Group 1', ['NORMAL_USER'])
    check_mapping(['Test Group Admins 1'], None, ['GROUP_ADMIN'])
    check_mapping(['Test Group Admins 3'], 'Sign Group 2', ['ACCOUNT_ADMIN', 'GROUP_ADMIN'])
    check_mapping(['Sign Group 1', 'Test Group Admins 1'], 'Sign Group 1', ['GROUP_ADMIN'])
    check_mapping(['Sign Group 1', 'Sign Group 2'], 'Sign Group 1', ['NORMAL_USER'])
    check_mapping(['Sign Group 3', 'Sign Group 2'], 'Sign Group 2', ['NORMAL_USER'])
    check_mapping(['Sign Group 3', 'Test Group Admins 1', 'Test Group Admins 2'],
                  'Sign Group 3', ['ACCOUNT_ADMIN', 'GROUP_ADMIN'])