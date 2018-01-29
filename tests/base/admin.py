import pytest

from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from django.test.client import RequestFactory

from pontoon.base.admin import UserAdmin
from pontoon.base.models import PermissionChangelog


@pytest.fixture
def user_form_request():
    """
    Mock for a request object which is passed to every django admin form.
    """
    def _get_user_form_request(request_user, user, **override_fields):
        rf = RequestFactory()
        fields = (
            'username',
            'email',
            'first_name',
            'last_name',
        )

        form_request = {f: (getattr(user, f, '') or '') for f in fields}
        form_request['date_joined_0'] = '2018-01-01'
        form_request['date_joined_1'] = '00:00:00'

        form_request.update(override_fields)

        request = rf.post(
            '/dummy/',
            form_request
        )
        request.user = request_user
        return request

    return _get_user_form_request


@pytest.fixture
def get_useradmin_form():
    """
    Get a UserAdmin form instance.
    """
    def _get_user_admin_form(request, user):
        useradmin = UserAdmin(
            User,
            AdminSite(),
        )
        form = useradmin.get_form(
            request=request,
            obj=user,
        )
        return useradmin, form(
            request.POST,
            instance=user,
            initial={'password': 'password'}
        )

    return _get_user_admin_form


@pytest.mark.django_db
def test_user_admin_form_log_no_changes(
    user0,
    user1,
    user_form_request,
    get_useradmin_form,
):
    _, form = get_useradmin_form(
        user_form_request(user0, user1),
        user1
    )

    assert form.is_valid()

    form.save()
    assert list(PermissionChangelog.objects.all()) == []


@pytest.mark.django_db
def test_user_admin_form_log_add_groups(
        locale0,
        user0,
        user1,
        user_form_request,
        get_useradmin_form,
        assert_permissionchangelog
):
    request = user_form_request(
        user0,
        user1,
        groups=[
            locale0.managers_group.pk,
        ]
    )
    useradmin, form = get_useradmin_form(
        request,
        user1
    )
    assert form.is_valid()

    useradmin.save_model(request, user1, form, True)

    changelog_entry0, = PermissionChangelog.objects.all()

    assert_permissionchangelog(
        changelog_entry0,
        'added',
        user0,
        user1,
        locale0.managers_group
    )


@pytest.mark.django_db
def test_user_admin_form_log_removed_groups(
        locale0,
        user0,
        user1,
        user_form_request,
        get_useradmin_form,
        assert_permissionchangelog
):

    user1.groups.add(locale0.managers_group)
    request = user_form_request(
        user0,
        user1,
        groups=[]
    )
    useradmin, form = get_useradmin_form(
        request,
        user1
    )
    assert form.is_valid()

    useradmin.save_model(request, user1, form, True)

    changelog_entry0, = PermissionChangelog.objects.all()

    assert_permissionchangelog(
        changelog_entry0,
        'removed',
        user0,
        user1,
        locale0.managers_group
    )